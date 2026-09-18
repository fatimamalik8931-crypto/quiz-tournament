from flask import Blueprint, jsonify, g

from db import get_connection
from auth_utils import require_auth

bp = Blueprint("users", __name__, url_prefix="/api/users")


@bp.get("/me/history")
@require_auth
def my_history():
    conn = get_connection()
    attempts = conn.execute(
        """SELECT qa.*, c.key as category_key, ct.name as category_name
           FROM quiz_attempts qa
           JOIN categories c ON c.id = qa.category_id
           LEFT JOIN category_translations ct ON ct.category_id = c.id AND ct.language = qa.language
           WHERE qa.user_id = ?
           ORDER BY qa.created_at DESC LIMIT 50""",
        (g.user["id"],),
    ).fetchall()
    tournaments = conn.execute(
        """SELECT tp.*, t.name as tournament_name, t.start_time
           FROM tournament_participants tp
           JOIN tournaments t ON t.id = tp.tournament_id
           WHERE tp.user_id = ?
           ORDER BY t.start_time DESC LIMIT 50""",
        (g.user["id"],),
    ).fetchall()
    conn.close()
    return jsonify({
        "practiceAttempts": [
            {
                "id": a["id"], "mode": "practice", "categoryName": a["category_name"] or a["category_key"],
                "score": a["score"], "correctCount": a["correct_count"], "totalQuestions": a["total_questions"],
                "createdAt": a["created_at"],
            }
            for a in attempts
        ],
        "tournaments": [
            {
                "id": t["id"], "mode": "tournament", "tournamentName": t["tournament_name"],
                "score": t["score"], "correctCount": t["correct_count"], "rank": t["rank"],
                "startTime": t["start_time"],
            }
            for t in tournaments
        ],
    })


@bp.get("/me/badges")
@require_auth
def my_badges():
    conn = get_connection()
    all_badges = conn.execute("SELECT * FROM badges").fetchall()
    earned = conn.execute(
        "SELECT badge_id, earned_at FROM user_badges WHERE user_id = ?", (g.user["id"],)
    ).fetchall()
    conn.close()
    earned_map = {e["badge_id"]: e["earned_at"] for e in earned}
    return jsonify({
        "badges": [
            {
                "key": b["key"], "name": b["name"], "description": b["description"], "icon": b["icon"],
                "earned": b["id"] in earned_map, "earnedAt": earned_map.get(b["id"]),
            }
            for b in all_badges
        ]
    })


@bp.get("/me/stats")
@require_auth
def my_stats():
    conn = get_connection()
    quizzes = conn.execute(
        "SELECT COUNT(*) as n, COALESCE(SUM(score),0) as pts FROM quiz_attempts WHERE user_id = ?",
        (g.user["id"],),
    ).fetchone()
    tournaments = conn.execute(
        "SELECT COUNT(*) as n FROM tournament_participants WHERE user_id = ?", (g.user["id"],)
    ).fetchone()
    wins = conn.execute(
        "SELECT COUNT(*) as n FROM tournament_participants WHERE user_id = ? AND rank = 1", (g.user["id"],)
    ).fetchone()
    conn.close()
    return jsonify({
        "totalPoints": g.user["total_points"],
        "quizzesPlayed": quizzes["n"],
        "tournamentsPlayed": tournaments["n"],
        "tournamentsWon": wins["n"],
    })
