from flask import Blueprint, request, jsonify

from db import get_connection
from helpers import normalize_lang

bp = Blueprint("leaderboard", __name__, url_prefix="/api/leaderboard")


@bp.get("/overall")
def overall_leaderboard():
    limit = min(int(request.args.get("limit", 50)), 200)
    conn = get_connection()
    rows = conn.execute(
        """SELECT id, name, total_points,
                  (SELECT COUNT(*) FROM quiz_attempts WHERE quiz_attempts.user_id = users.id) as quizzes_played
           FROM users
           ORDER BY total_points DESC, name ASC
           LIMIT ?""",
        (limit,),
    ).fetchall()
    conn.close()
    out = [
        {"rank": i + 1, "userId": r["id"], "name": r["name"], "points": r["total_points"],
         "quizzesPlayed": r["quizzes_played"]}
        for i, r in enumerate(rows)
    ]
    return jsonify({"leaderboard": out})


@bp.get("/category/<category_id>")
def category_leaderboard(category_id):
    limit = min(int(request.args.get("limit", 50)), 200)
    lang = normalize_lang(request.args.get("lang", "en"))
    conn = get_connection()
    category = conn.execute("SELECT * FROM categories WHERE id = ?", (category_id,)).fetchone()
    if not category:
        conn.close()
        return jsonify({"error": "Category not found"}), 404
    tr = conn.execute(
        "SELECT name FROM category_translations WHERE category_id = ? AND language = ?",
        (category_id, lang),
    ).fetchone()
    rows = conn.execute(
        """SELECT u.id, u.name, SUM(qa.score) as points, COUNT(*) as attempts
           FROM quiz_attempts qa
           JOIN users u ON u.id = qa.user_id
           WHERE qa.category_id = ?
           GROUP BY u.id
           ORDER BY points DESC
           LIMIT ?""",
        (category_id, limit),
    ).fetchall()
    conn.close()
    out = [
        {"rank": i + 1, "userId": r["id"], "name": r["name"], "points": r["points"], "attempts": r["attempts"]}
        for i, r in enumerate(rows)
    ]
    return jsonify({"leaderboard": out, "categoryName": tr["name"] if tr else category["key"]})
