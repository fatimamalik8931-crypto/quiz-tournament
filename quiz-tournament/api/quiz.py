"""Practice mode: solo quiz play anytime, no tournament pressure."""
import random

from flask import Blueprint, request, jsonify, g

from db import get_connection, new_id
from auth_utils import require_auth
from helpers import question_public_dict, fetch_translations, normalize_lang, award_badge
from scoring import compute_score

bp = Blueprint("quiz", __name__, url_prefix="/api/quiz")


@bp.post("/start")
@require_auth
def start_quiz():
    data = request.get_json(silent=True) or {}
    category_id = data.get("categoryId")
    lang = normalize_lang(data.get("language", g.user.get("preferred_language", "en")))
    count = min(max(int(data.get("count", 10)), 3), 25)

    if not category_id:
        return jsonify({"error": "categoryId is required"}), 400

    conn = get_connection()
    category = conn.execute("SELECT * FROM categories WHERE id = ?", (category_id,)).fetchone()
    if not category:
        conn.close()
        return jsonify({"error": "Category not found"}), 404

    all_qs = conn.execute("SELECT * FROM questions WHERE category_id = ?", (category_id,)).fetchall()
    if not all_qs:
        conn.close()
        return jsonify({"error": "This category has no questions yet"}), 404

    chosen = random.sample(list(all_qs), min(count, len(all_qs)))
    trans = fetch_translations(conn, "question_translations", "question_id", [q["id"] for q in chosen])

    attempt_id = new_id()
    conn.execute(
        "INSERT INTO quiz_attempts (id, user_id, category_id, language, total_questions) VALUES (?,?,?,?,?)",
        (attempt_id, g.user["id"], category_id, lang, len(chosen)),
    )
    conn.commit()
    conn.close()

    questions = [question_public_dict(q, trans.get(q["id"], {}), lang) for q in chosen]
    return jsonify({"attemptId": attempt_id, "questions": questions})


@bp.post("/answer")
@require_auth
def answer_question():
    data = request.get_json(silent=True) or {}
    attempt_id = data.get("attemptId")
    question_id = data.get("questionId")
    selected_index = data.get("selectedIndex")
    time_ms = int(data.get("timeMs", 0))

    conn = get_connection()
    attempt = conn.execute(
        "SELECT * FROM quiz_attempts WHERE id = ? AND user_id = ?", (attempt_id, g.user["id"])
    ).fetchone()
    if not attempt:
        conn.close()
        return jsonify({"error": "Attempt not found"}), 404

    already = conn.execute(
        "SELECT id FROM quiz_answers WHERE attempt_id = ? AND question_id = ?", (attempt_id, question_id)
    ).fetchone()
    if already:
        conn.close()
        return jsonify({"error": "This question was already answered"}), 409

    question = conn.execute("SELECT * FROM questions WHERE id = ?", (question_id,)).fetchone()
    if not question:
        conn.close()
        return jsonify({"error": "Question not found"}), 404

    correct = selected_index is not None and int(selected_index) == question["correct_index"]
    points = compute_score(question["points"], question["time_limit_seconds"], time_ms, correct)

    conn.execute(
        "INSERT INTO quiz_answers (id, attempt_id, question_id, selected_index, correct, time_ms) VALUES (?,?,?,?,?,?)",
        (new_id(), attempt_id, question_id, selected_index, 1 if correct else 0, time_ms),
    )
    conn.execute(
        "UPDATE quiz_attempts SET score = score + ?, correct_count = correct_count + ? WHERE id = ?",
        (points, 1 if correct else 0, attempt_id),
    )
    conn.commit()
    conn.close()

    return jsonify({
        "correct": correct,
        "correctIndex": question["correct_index"],
        "pointsAwarded": points,
    })


@bp.post("/finish")
@require_auth
def finish_quiz():
    data = request.get_json(silent=True) or {}
    attempt_id = data.get("attemptId")

    conn = get_connection()
    attempt = conn.execute(
        "SELECT * FROM quiz_attempts WHERE id = ? AND user_id = ?", (attempt_id, g.user["id"])
    ).fetchone()
    if not attempt:
        conn.close()
        return jsonify({"error": "Attempt not found"}), 404

    conn.execute(
        "UPDATE users SET total_points = total_points + ? WHERE id = ?",
        (attempt["score"], g.user["id"]),
    )

    badges_awarded = []
    total_attempts = conn.execute(
        "SELECT COUNT(*) as n FROM quiz_attempts WHERE user_id = ?", (g.user["id"],)
    ).fetchone()["n"]

    if total_attempts >= 1:
        b = award_badge(conn, g.user["id"], "first_quiz")
        if b:
            badges_awarded.append(b["name"])
    if total_attempts >= 10:
        b = award_badge(conn, g.user["id"], "ten_quizzes")
        if b:
            badges_awarded.append(b["name"])
    if attempt["total_questions"] > 0 and attempt["correct_count"] == attempt["total_questions"]:
        b = award_badge(conn, g.user["id"], "perfect_score")
        if b:
            badges_awarded.append(b["name"])

    fast_correct = conn.execute(
        "SELECT COUNT(*) as n FROM quiz_answers WHERE attempt_id = ? AND correct = 1 AND time_ms < 3000",
        (attempt_id,),
    ).fetchone()["n"]
    if fast_correct > 0:
        b = award_badge(conn, g.user["id"], "speed_demon")
        if b:
            badges_awarded.append(b["name"])

    conn.commit()
    result = {
        "score": attempt["score"],
        "correctCount": attempt["correct_count"],
        "totalQuestions": attempt["total_questions"],
        "badgesAwarded": badges_awarded,
    }
    conn.close()
    return jsonify(result)
