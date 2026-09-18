from flask import Blueprint, request, jsonify

from db import get_connection
from helpers import category_to_dict, fetch_translations, normalize_lang

bp = Blueprint("categories", __name__, url_prefix="/api/categories")


@bp.get("")
def list_categories():
    lang = normalize_lang(request.args.get("lang", "en"))
    conn = get_connection()
    cats = conn.execute("SELECT * FROM categories ORDER BY created_at").fetchall()
    trans = fetch_translations(conn, "category_translations", "category_id", [c["id"] for c in cats])
    counts = {
        r["category_id"]: r["n"]
        for r in conn.execute(
            "SELECT category_id, COUNT(*) as n FROM questions GROUP BY category_id"
        ).fetchall()
    }
    conn.close()
    out = []
    for c in cats:
        d = category_to_dict(c, trans.get(c["id"], {}), lang)
        d["questionCount"] = counts.get(c["id"], 0)
        out.append(d)
    return jsonify({"categories": out})
