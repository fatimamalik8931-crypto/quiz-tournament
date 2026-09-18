"""Tournament mode: scheduled tournaments where multiple users compete within
a shared time window, progressing through the same questions in lock-step
(computed from wall-clock time, so no background scheduler process is
needed), ranked by score + answer speed. Live progress is pushed to clients
over Server-Sent Events (a plain HTTP stream every browser supports natively
via EventSource - no extra library required).
"""
import json
import random
import time
from datetime import datetime, timezone

from flask import Blueprint, request, jsonify, g, Response, stream_with_context

from db import get_connection, new_id
from auth_utils import require_auth, require_admin
from helpers import question_public_dict, fetch_translations, normalize_lang, award_badge

bp = Blueprint("tournaments", __name__, url_prefix="/api/tournaments")


# ---------------------------------------------------------------------------
# time / phase helpers
# ---------------------------------------------------------------------------
def now_utc():
    return datetime.now(timezone.utc)


def parse_iso(s):
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def to_iso(dt):
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def compute_phase(tournament_row, num_questions):
    """Returns (phase, current_index, ms_into_question, ms_remaining_in_question)."""
    if tournament_row["status"] == "CANCELLED":
        return "CANCELLED", -1, 0, 0
    start = parse_iso(tournament_row["start_time"])
    now = now_utc()
    per_q_ms = tournament_row["per_question_secs"] * 1000
    if now < start or num_questions == 0:
        return "SCHEDULED", -1, 0, 0
    elapsed_ms = int((now - start).total_seconds() * 1000)
    idx = elapsed_ms // per_q_ms
    if idx >= num_questions:
        return "COMPLETED", num_questions, 0, 0
    ms_into = elapsed_ms - idx * per_q_ms
    return "LIVE", int(idx), int(ms_into), int(per_q_ms - ms_into)


def get_tournament_questions(conn, tournament_id):
    rows = conn.execute(
        """SELECT q.*, tq.position FROM tournament_questions tq
           JOIN questions q ON q.id = tq.question_id
           WHERE tq.tournament_id = ? ORDER BY tq.position""",
        (tournament_id,),
    ).fetchall()
    return rows


def finalize_if_completed(conn, tournament, questions):
    """Once a tournament's time window has fully elapsed, lock in ranks, pay
    out points to each participant's profile, and hand out the winner badge.
    Idempotent: only touches participants that haven't been finalized yet."""
    phase, *_ = compute_phase(tournament, len(questions))
    if phase != "COMPLETED":
        return
    participants = conn.execute(
        "SELECT * FROM tournament_participants WHERE tournament_id = ? AND finished_at IS NULL",
        (tournament["id"],),
    ).fetchall()
    if not participants:
        return
    all_participants = conn.execute(
        "SELECT * FROM tournament_participants WHERE tournament_id = ? ORDER BY score DESC, total_time_ms ASC",
        (tournament["id"],),
    ).fetchall()
    for rank, p in enumerate(all_participants, start=1):
        conn.execute(
            "UPDATE tournament_participants SET rank = ?, finished_at = COALESCE(finished_at, ?) WHERE id = ?",
            (rank, to_iso(now_utc()), p["id"]),
        )
        if p["finished_at"] is None:
            conn.execute(
                "UPDATE users SET total_points = total_points + ? WHERE id = ?",
                (p["score"], p["user_id"]),
            )
            if rank == 1 and p["score"] > 0:
                award_badge(conn, p["user_id"], "tournament_winner")
    conn.commit()


def participant_dict(row, name):
    return {
        "userId": row["user_id"],
        "name": name,
        "score": row["score"],
        "correctCount": row["correct_count"],
        "totalTimeMs": row["total_time_ms"],
        "rank": row["rank"],
    }


def tournament_summary(conn, t, lang, user_id=None):
    questions = get_tournament_questions(conn, t["id"])
    finalize_if_completed(conn, t, questions)
    phase, idx, ms_into, ms_remaining = compute_phase(t, len(questions))
    count = conn.execute(
        "SELECT COUNT(*) as n FROM tournament_participants WHERE tournament_id = ?", (t["id"],)
    ).fetchone()["n"]
    cat_name = None
    if t["category_id"]:
        cat = conn.execute("SELECT * FROM categories WHERE id = ?", (t["category_id"],)).fetchone()
        if cat:
            tr = conn.execute(
                "SELECT * FROM category_translations WHERE category_id = ? AND language = ?",
                (cat["id"], lang),
            ).fetchone()
            cat_name = tr["name"] if tr else cat["key"]
    joined = False
    if user_id:
        joined = conn.execute(
            "SELECT id FROM tournament_participants WHERE tournament_id = ? AND user_id = ?",
            (t["id"], user_id),
        ).fetchone() is not None
    return {
        "id": t["id"],
        "name": t["name"],
        "categoryId": t["category_id"],
        "categoryName": cat_name,
        "startTime": t["start_time"],
        "durationMinutes": t["duration_minutes"],
        "perQuestionSecs": t["per_question_secs"],
        "numQuestions": len(questions),
        "phase": phase,
        "currentIndex": idx,
        "msRemainingInQuestion": ms_remaining,
        "participantCount": count,
        "joined": joined,
    }


# ---------------------------------------------------------------------------
# routes
# ---------------------------------------------------------------------------
@bp.get("")
def list_tournaments():
    lang = normalize_lang(request.args.get("lang", "en"))
    conn = get_connection()
    rows = conn.execute("SELECT * FROM tournaments ORDER BY start_time DESC").fetchall()
    user_id = g.user["id"] if getattr(g, "user", None) else None
    out = [tournament_summary(conn, t, lang, user_id) for t in rows]
    conn.close()
    return jsonify({"tournaments": out})


@bp.post("")
@require_admin
def create_tournament():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    category_id = data.get("categoryId")
    start_time = data.get("startTime")
    duration_minutes = int(data.get("durationMinutes", 10))
    per_question_secs = int(data.get("perQuestionSecs", 20))
    question_count = int(data.get("questionCount", 10))

    if not name or not start_time:
        return jsonify({"error": "name and startTime are required"}), 400
    try:
        parse_iso(start_time)
    except ValueError:
        return jsonify({"error": "startTime must be an ISO 8601 datetime"}), 400

    conn = get_connection()
    if category_id:
        pool = conn.execute("SELECT id FROM questions WHERE category_id = ?", (category_id,)).fetchall()
    else:
        pool = conn.execute("SELECT id FROM questions").fetchall()
    if len(pool) < 3:
        conn.close()
        return jsonify({"error": "Not enough questions available to build this tournament"}), 400

    chosen = random.sample(list(pool), min(question_count, len(pool)))
    tid = new_id()
    conn.execute(
        """INSERT INTO tournaments (id, name, category_id, start_time, duration_minutes, per_question_secs, status)
           VALUES (?,?,?,?,?,?,'SCHEDULED')""",
        (tid, name, category_id, start_time, duration_minutes, per_question_secs),
    )
    for i, q in enumerate(chosen):
        conn.execute(
            "INSERT INTO tournament_questions (id, tournament_id, question_id, position) VALUES (?,?,?,?)",
            (new_id(), tid, q["id"], i),
        )
    conn.commit()
    t = conn.execute("SELECT * FROM tournaments WHERE id = ?", (tid,)).fetchone()
    out = tournament_summary(conn, t, "en")
    conn.close()
    return jsonify({"tournament": out}), 201


@bp.get("/<tid>")
def get_tournament(tid):
    lang = normalize_lang(request.args.get("lang", "en"))
    conn = get_connection()
    t = conn.execute("SELECT * FROM tournaments WHERE id = ?", (tid,)).fetchone()
    if not t:
        conn.close()
        return jsonify({"error": "Tournament not found"}), 404
    user_id = g.user["id"] if getattr(g, "user", None) else None
    out = tournament_summary(conn, t, lang, user_id)
    conn.close()
    return jsonify({"tournament": out})


@bp.post("/<tid>/join")
@require_auth
def join_tournament(tid):
    conn = get_connection()
    t = conn.execute("SELECT * FROM tournaments WHERE id = ?", (tid,)).fetchone()
    if not t:
        conn.close()
        return jsonify({"error": "Tournament not found"}), 404
    questions = get_tournament_questions(conn, tid)
    phase, *_ = compute_phase(t, len(questions))
    if phase == "COMPLETED" or phase == "CANCELLED":
        conn.close()
        return jsonify({"error": "This tournament is no longer joinable"}), 409

    existing = conn.execute(
        "SELECT id FROM tournament_participants WHERE tournament_id = ? AND user_id = ?", (tid, g.user["id"])
    ).fetchone()
    if not existing:
        conn.execute(
            "INSERT INTO tournament_participants (id, tournament_id, user_id) VALUES (?,?,?)",
            (new_id(), tid, g.user["id"]),
        )
        conn.commit()
    conn.close()
    return jsonify({"joined": True})


@bp.get("/<tid>/question")
@require_auth
def current_question(tid):
    lang = normalize_lang(request.args.get("lang", g.user.get("preferred_language", "en")))
    conn = get_connection()
    t = conn.execute("SELECT * FROM tournaments WHERE id = ?", (tid,)).fetchone()
    if not t:
        conn.close()
        return jsonify({"error": "Tournament not found"}), 404
    participant = conn.execute(
        "SELECT * FROM tournament_participants WHERE tournament_id = ? AND user_id = ?", (tid, g.user["id"])
    ).fetchone()
    if not participant:
        conn.close()
        return jsonify({"error": "Join the tournament first"}), 403

    questions = get_tournament_questions(conn, tid)
    finalize_if_completed(conn, t, questions)
    phase, idx, ms_into, ms_remaining = compute_phase(t, len(questions))

    if phase == "SCHEDULED":
        conn.close()
        return jsonify({"phase": phase, "startTime": t["start_time"]})
    if phase in ("COMPLETED", "CANCELLED"):
        conn.close()
        return jsonify({"phase": phase})

    q = questions[idx]
    trans = fetch_translations(conn, "question_translations", "question_id", [q["id"]])
    already_answered = conn.execute(
        "SELECT id FROM tournament_answers WHERE participant_id = ? AND question_id = ?",
        (participant["id"], q["id"]),
    ).fetchone() is not None
    conn.close()

    return jsonify({
        "phase": phase,
        "index": idx,
        "total": len(questions),
        "msRemaining": ms_remaining,
        "perQuestionSecs": t["per_question_secs"],
        "alreadyAnswered": already_answered,
        "question": question_public_dict(q, trans.get(q["id"], {}), lang),
    })


@bp.post("/<tid>/answer")
@require_auth
def answer_tournament_question(tid):
    data = request.get_json(silent=True) or {}
    question_index = data.get("questionIndex")
    selected_index = data.get("selectedIndex")
    time_ms = int(data.get("timeMs", 0))

    conn = get_connection()
    t = conn.execute("SELECT * FROM tournaments WHERE id = ?", (tid,)).fetchone()
    if not t:
        conn.close()
        return jsonify({"error": "Tournament not found"}), 404
    participant = conn.execute(
        "SELECT * FROM tournament_participants WHERE tournament_id = ? AND user_id = ?", (tid, g.user["id"])
    ).fetchone()
    if not participant:
        conn.close()
        return jsonify({"error": "Join the tournament first"}), 403

    questions = get_tournament_questions(conn, tid)
    phase, idx, *_ = compute_phase(t, len(questions))
    if phase != "LIVE" or question_index != idx:
        conn.close()
        return jsonify({"error": "This question is no longer accepting answers"}), 409

    q = questions[idx]
    already = conn.execute(
        "SELECT id FROM tournament_answers WHERE participant_id = ? AND question_id = ?",
        (participant["id"], q["id"]),
    ).fetchone()
    if already:
        conn.close()
        return jsonify({"error": "Already answered"}), 409

    correct = selected_index is not None and int(selected_index) == q["correct_index"]
    from scoring import compute_score
    points = compute_score(q["points"], t["per_question_secs"], time_ms, correct)

    conn.execute(
        "INSERT INTO tournament_answers (id, participant_id, question_id, selected_index, correct, time_ms) VALUES (?,?,?,?,?,?)",
        (new_id(), participant["id"], q["id"], selected_index, 1 if correct else 0, time_ms),
    )
    conn.execute(
        """UPDATE tournament_participants
           SET score = score + ?, correct_count = correct_count + ?, total_time_ms = total_time_ms + ?
           WHERE id = ?""",
        (points, 1 if correct else 0, time_ms, participant["id"]),
    )
    conn.commit()
    conn.close()
    return jsonify({"correct": correct, "correctIndex": q["correct_index"], "pointsAwarded": points})


@bp.get("/<tid>/leaderboard")
def tournament_leaderboard(tid):
    conn = get_connection()
    t = conn.execute("SELECT * FROM tournaments WHERE id = ?", (tid,)).fetchone()
    if not t:
        conn.close()
        return jsonify({"error": "Tournament not found"}), 404
    questions = get_tournament_questions(conn, tid)
    finalize_if_completed(conn, t, questions)
    rows = conn.execute(
        """SELECT tp.*, u.name FROM tournament_participants tp
           JOIN users u ON u.id = tp.user_id
           WHERE tp.tournament_id = ?
           ORDER BY tp.score DESC, tp.total_time_ms ASC""",
        (tid,),
    ).fetchall()
    conn.close()
    out = [participant_dict(r, r["name"]) for r in rows]
    for i, r in enumerate(out, start=1):
        if r["rank"] is None:
            r["rank"] = i
    return jsonify({"leaderboard": out})


@bp.get("/<tid>/stream")
def tournament_stream(tid):
    """Server-Sent Events: pushes tournament phase + live mini-leaderboard
    about once a second, so lobby and play screens update without polling."""

    def event_stream():
        last_payload = None
        ticks = 0
        while ticks < 60 * 30:  # safety cap: ~30 minutes per open connection
            conn = get_connection()
            t = conn.execute("SELECT * FROM tournaments WHERE id = ?", (tid,)).fetchone()
            if not t:
                conn.close()
                yield "event: error\ndata: {}\n\n"
                return
            questions = get_tournament_questions(conn, tid)
            finalize_if_completed(conn, t, questions)
            phase, idx, ms_into, ms_remaining = compute_phase(t, len(questions))
            rows = conn.execute(
                """SELECT tp.*, u.name FROM tournament_participants tp
                   JOIN users u ON u.id = tp.user_id
                   WHERE tp.tournament_id = ?
                   ORDER BY tp.score DESC, tp.total_time_ms ASC LIMIT 5""",
                (tid,),
            ).fetchall()
            count = conn.execute(
                "SELECT COUNT(*) as n FROM tournament_participants WHERE tournament_id = ?", (tid,)
            ).fetchone()["n"]
            conn.close()

            payload = {
                "phase": phase,
                "currentIndex": idx,
                "msRemainingInQuestion": ms_remaining,
                "numQuestions": len(questions),
                "participantCount": count,
                "leaderboard": [participant_dict(r, r["name"]) for r in rows],
            }
            encoded = json.dumps(payload)
            if encoded != last_payload:
                yield f"data: {encoded}\n\n"
                last_payload = encoded
            else:
                yield ": keep-alive\n\n"
            if phase in ("COMPLETED", "CANCELLED"):
                return
            time.sleep(1)
            ticks += 1

    return Response(
        stream_with_context(event_stream()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@bp.post("/<tid>/cancel")
@require_admin
def cancel_tournament(tid):
    conn = get_connection()
    conn.execute("UPDATE tournaments SET status = 'CANCELLED' WHERE id = ?", (tid,))
    conn.commit()
    conn.close()
    return jsonify({"cancelled": True})
