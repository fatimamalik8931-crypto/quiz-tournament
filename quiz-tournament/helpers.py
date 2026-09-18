"""Small shared helpers for translating rows and awarding badges."""
import json

from db import get_connection, new_id

SUPPORTED_LANGUAGES = ["en", "ur"]
DEFAULT_LANGUAGE = "en"


def normalize_lang(lang):
    return lang if lang in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE


def category_to_dict(cat_row, translations_by_lang, lang):
    lang = normalize_lang(lang)
    t = translations_by_lang.get(lang) or translations_by_lang.get(DEFAULT_LANGUAGE) or {}
    return {
        "id": cat_row["id"],
        "key": cat_row["key"],
        "icon": cat_row["icon"],
        "colorFrom": cat_row["color_from"],
        "colorTo": cat_row["color_to"],
        "name": t.get("name", cat_row["key"]),
        "description": t.get("description", ""),
    }


def question_public_dict(q_row, translations_by_lang, lang):
    """Question shape sent to players — no correct_index."""
    lang = normalize_lang(lang)
    t = translations_by_lang.get(lang) or translations_by_lang.get(DEFAULT_LANGUAGE) or {}
    return {
        "id": q_row["id"],
        "categoryId": q_row["category_id"],
        "difficulty": q_row["difficulty"],
        "points": q_row["points"],
        "timeLimitSeconds": q_row["time_limit_seconds"],
        "text": t.get("text", ""),
        "options": json.loads(t.get("options_json", "[]")),
    }


def question_admin_dict(q_row, translations_by_lang):
    """Full question shape (all languages + answer) for the admin panel."""
    return {
        "id": q_row["id"],
        "categoryId": q_row["category_id"],
        "difficulty": q_row["difficulty"],
        "points": q_row["points"],
        "timeLimitSeconds": q_row["time_limit_seconds"],
        "correctIndex": q_row["correct_index"],
        "translations": {
            lang: {"text": t["text"], "options": json.loads(t["options_json"])}
            for lang, t in translations_by_lang.items()
        },
    }


def fetch_translations(conn, table, fk_column, ids):
    """Return {parent_id: {lang: row_dict}} for a translations table."""
    if not ids:
        return {}
    placeholders = ",".join("?" for _ in ids)
    rows = conn.execute(
        f"SELECT * FROM {table} WHERE {fk_column} IN ({placeholders})", ids
    ).fetchall()
    out = {}
    for r in rows:
        d = dict(r)
        out.setdefault(d[fk_column], {})[d["language"]] = d
    return out


def award_badge(conn, user_id, badge_key):
    """Grant a badge if the user doesn't already have it. Returns badge dict or None."""
    badge = conn.execute("SELECT * FROM badges WHERE key = ?", (badge_key,)).fetchone()
    if not badge:
        return None
    already = conn.execute(
        "SELECT id FROM user_badges WHERE user_id = ? AND badge_id = ?", (user_id, badge["id"])
    ).fetchone()
    if already:
        return None
    conn.execute(
        "INSERT INTO user_badges (id, user_id, badge_id) VALUES (?,?,?)",
        (new_id(), user_id, badge["id"]),
    )
    return dict(badge)
