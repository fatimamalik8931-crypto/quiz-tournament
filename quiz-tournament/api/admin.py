"""Admin panel API: manage categories/questions per language, schedule
tournaments (creation lives in tournaments.py, guarded by @require_admin),
and view user/platform stats.
"""
import json
import sqlite3

from flask import Blueprint, request, jsonify

from db import get_connection, new_id
from auth_utils import require_admin
from helpers import question_admin_dict, fetch_translations, SUPPORTED_LANGUAGES

bp = Blueprint("admin", __name__, url_prefix="/api/admin")


@bp.get("/stats")
@require_admin
def stats():
    conn = get_connection()
    users_n = conn.execute("SELECT COUNT(*) as n FROM users").fetchone()["n"]
    questions_n = conn.execute("SELECT COUNT(*) as n FROM questions").fetchone()["n"]
    attempts_n = conn.execute("SELECT COUNT(*) as n FROM quiz_attempts").fetchone()["n"]
    tournaments_n = conn.execute("SELECT COUNT(*) as n FROM tournaments").fetchone()["n"]
    active_tournaments = conn.execute(
        "SELECT COUNT(*) as n FROM tournaments WHERE status != 'CANCELLED'"
    ).fetchone()["n"]
    top_categories = conn.execute(
        """SELECT c.key, ct.name, COUNT(qa.id) as plays
           FROM quiz_attempts qa
           JOIN categories c ON c.id = qa.category_id
           LEFT JOIN category_translations ct ON ct.category_id = c.id AND ct.language = 'en'
           GROUP BY c.id ORDER BY plays DESC LIMIT 6"""
    ).fetchall()
    conn.close()
    return jsonify({
        "users": users_n,
        "questions": questions_n,
        "quizAttempts": attempts_n,
        "tournaments": tournaments_n,
        "activeTournaments": active_tournaments,
        "topCategories": [{"key": r["key"], "name": r["name"] or r["key"], "plays": r["plays"]} for r in top_categories],
    })


@bp.get("/users")
@require_admin
def list_users():
    conn = get_connection()
    rows = conn.execute(
        """SELECT u.id, u.name, u.email, u.role, u.total_points, u.created_at,
                  (SELECT COUNT(*) FROM quiz_attempts WHERE user_id = u.id) as quizzes_played,
                  (SELECT COUNT(*) FROM tournament_participants WHERE user_id = u.id) as tournaments_played
           FROM users u ORDER BY u.created_at DESC"""
    ).fetchall()
    conn.close()
    return jsonify({"users": [
        {
            "id": r["id"], "name": r["name"], "email": r["email"], "role": r["role"],
            "totalPoints": r["total_points"], "quizzesPlayed": r["quizzes_played"],
            "tournamentsPlayed": r["tournaments_played"], "createdAt": r["created_at"],
        } for r in rows
    ]})


# ---------------------------------------------------------------------------
# Categories
# ---------------------------------------------------------------------------
@bp.post("/categories")
@require_admin
def create_category():
    data = request.get_json(silent=True) or {}
    key = (data.get("key") or "").strip().lower().replace(" ", "_")
    icon = data.get("icon") or "book"
    color_from = data.get("colorFrom") or "#7C3AED"
    color_to = data.get("colorTo") or "#C026D3"
    translations = data.get("translations") or {}

    if not key or "en" not in translations or not translations["en"].get("name"):
        return jsonify({"error": "key and an English name are required"}), 400

    conn = get_connection()
    existing = conn.execute("SELECT id FROM categories WHERE key = ?", (key,)).fetchone()
    if existing:
        conn.close()
        return jsonify({"error": "A category with this key already exists"}), 409

    cid = new_id()
    conn.execute(
        "INSERT INTO categories (id, key, icon, color_from, color_to) VALUES (?,?,?,?,?)",
        (cid, key, icon, color_from, color_to),
    )
    for lang, t in translations.items():
        if lang not in SUPPORTED_LANGUAGES:
            continue
        conn.execute(
            "INSERT INTO category_translations (id, category_id, language, name, description) VALUES (?,?,?,?,?)",
            (new_id(), cid, lang, t.get("name", ""), t.get("description", "")),
        )
    conn.commit()
    conn.close()
    return jsonify({"id": cid}), 201


@bp.put("/categories/<cid>")
@require_admin
def update_category(cid):
    data = request.get_json(silent=True) or {}
    conn = get_connection()
    cat = conn.execute("SELECT * FROM categories WHERE id = ?", (cid,)).fetchone()
    if not cat:
        conn.close()
        return jsonify({"error": "Category not found"}), 404

    fields, values = [], []
    for col, key in (("icon", "icon"), ("color_from", "colorFrom"), ("color_to", "colorTo")):
        if key in data:
            fields.append(f"{col} = ?")
            values.append(data[key])
    if fields:
        values.append(cid)
        conn.execute(f"UPDATE categories SET {', '.join(fields)} WHERE id = ?", values)

    for lang, t in (data.get("translations") or {}).items():
        if lang not in SUPPORTED_LANGUAGES:
            continue
        existing = conn.execute(
            "SELECT id FROM category_translations WHERE category_id = ? AND language = ?", (cid, lang)
        ).fetchone()
        if existing:
            conn.execute(
                "UPDATE category_translations SET name = ?, description = ? WHERE id = ?",
                (t.get("name", ""), t.get("description", ""), existing["id"]),
            )
        else:
            conn.execute(
                "INSERT INTO category_translations (id, category_id, language, name, description) VALUES (?,?,?,?,?)",
                (new_id(), cid, lang, t.get("name", ""), t.get("description", "")),
            )
    conn.commit()
    conn.close()
    return jsonify({"updated": True})


@bp.delete("/categories/<cid>")
@require_admin
def delete_category(cid):
    conn = get_connection()
    try:
        conn.execute("DELETE FROM categories WHERE id = ?", (cid,))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({"error": "Can't delete: this category has quiz history tied to it."}), 400
    conn.close()
    return jsonify({"deleted": True})


# ---------------------------------------------------------------------------
# Questions
# ---------------------------------------------------------------------------
@bp.get("/questions")
@require_admin
def list_questions():
    category_id = request.args.get("categoryId")
    conn = get_connection()
    if category_id:
        rows = conn.execute(
            "SELECT * FROM questions WHERE category_id = ? ORDER BY created_at DESC", (category_id,)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM questions ORDER BY created_at DESC").fetchall()
    trans = fetch_translations(conn, "question_translations", "question_id", [r["id"] for r in rows])
    conn.close()
    return jsonify({"questions": [question_admin_dict(r, trans.get(r["id"], {})) for r in rows]})


@bp.post("/questions")
@require_admin
def create_question():
    data = request.get_json(silent=True) or {}
    category_id = data.get("categoryId")
    difficulty = data.get("difficulty", "medium")
    points = int(data.get("points", 10))
    time_limit = int(data.get("timeLimitSeconds", 20))
    correct_index = data.get("correctIndex")
    translations = data.get("translations") or {}

    if not category_id or correct_index is None or "en" not in translations:
        return jsonify({"error": "categoryId, correctIndex, and an English translation are required"}), 400
    correct_index = int(correct_index)
    if not (0 <= correct_index <= 3):
        return jsonify({"error": "correctIndex must be between 0 and 3"}), 400

    conn = get_connection()
    category = conn.execute("SELECT id FROM categories WHERE id = ?", (category_id,)).fetchone()
    if not category:
        conn.close()
        return jsonify({"error": "Category not found"}), 404

    for lang, t in translations.items():
        if len(t.get("options", [])) != 4:
            conn.close()
            return jsonify({"error": f"'{lang}' translation must have exactly 4 options"}), 400

    qid = new_id()
    conn.execute(
        "INSERT INTO questions (id, category_id, difficulty, points, time_limit_seconds, correct_index) VALUES (?,?,?,?,?,?)",
        (qid, category_id, difficulty, points, time_limit, correct_index),
    )
    for lang, t in translations.items():
        if lang not in SUPPORTED_LANGUAGES:
            continue
        conn.execute(
            "INSERT INTO question_translations (id, question_id, language, text, options_json) VALUES (?,?,?,?,?)",
            (new_id(), qid, lang, t.get("text", ""), json.dumps(t.get("options", []), ensure_ascii=False)),
        )
    conn.commit()
    conn.close()
    return jsonify({"id": qid}), 201


@bp.put("/questions/<qid>")
@require_admin
def update_question(qid):
    data = request.get_json(silent=True) or {}
    conn = get_connection()
    q = conn.execute("SELECT * FROM questions WHERE id = ?", (qid,)).fetchone()
    if not q:
        conn.close()
        return jsonify({"error": "Question not found"}), 404

    fields, values = [], []
    if "difficulty" in data:
        fields.append("difficulty = ?"); values.append(data["difficulty"])
    if "points" in data:
        fields.append("points = ?"); values.append(int(data["points"]))
    if "timeLimitSeconds" in data:
        fields.append("time_limit_seconds = ?"); values.append(int(data["timeLimitSeconds"]))
    if "correctIndex" in data:
        fields.append("correct_index = ?"); values.append(int(data["correctIndex"]))
    if "categoryId" in data:
        fields.append("category_id = ?"); values.append(data["categoryId"])
    if fields:
        fields.append("updated_at = strftime('%Y-%m-%dT%H:%M:%fZ','now')")
        values.append(qid)
        conn.execute(f"UPDATE questions SET {', '.join(fields)} WHERE id = ?", values)

    for lang, t in (data.get("translations") or {}).items():
        if lang not in SUPPORTED_LANGUAGES:
            continue
        existing = conn.execute(
            "SELECT id FROM question_translations WHERE question_id = ? AND language = ?", (qid, lang)
        ).fetchone()
        options_json = json.dumps(t.get("options", []), ensure_ascii=False)
        if existing:
            conn.execute(
                "UPDATE question_translations SET text = ?, options_json = ? WHERE id = ?",
                (t.get("text", ""), options_json, existing["id"]),
            )
        else:
            conn.execute(
                "INSERT INTO question_translations (id, question_id, language, text, options_json) VALUES (?,?,?,?,?)",
                (new_id(), qid, lang, t.get("text", ""), options_json),
            )
    conn.commit()
    conn.close()
    return jsonify({"updated": True})


@bp.delete("/questions/<qid>")
@require_admin
def delete_question(qid):
    conn = get_connection()
    try:
        conn.execute("DELETE FROM questions WHERE id = ?", (qid,))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({"error": "Can't delete: this question is used in a tournament or someone's quiz history."}), 400
    conn.close()
    return jsonify({"deleted": True})
