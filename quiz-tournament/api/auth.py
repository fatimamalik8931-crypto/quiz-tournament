import re

from flask import Blueprint, request, jsonify, g

from db import get_connection, new_id
from auth_utils import hash_password, verify_password, issue_token, public_user, require_auth

bp = Blueprint("auth", __name__, url_prefix="/api/auth")

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@bp.post("/register")
def register():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    preferred_language = data.get("preferredLanguage") or "en"

    if not name or len(name) < 2:
        return jsonify({"error": "Please enter your full name."}), 400
    if not EMAIL_RE.match(email):
        return jsonify({"error": "Please enter a valid email address."}), 400
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters."}), 400

    conn = get_connection()
    existing = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
    if existing:
        conn.close()
        return jsonify({"error": "An account with this email already exists."}), 409

    uid = new_id()
    conn.execute(
        "INSERT INTO users (id, name, email, password_hash, role, preferred_language) VALUES (?,?,?,?,?,?)",
        (uid, name, email, hash_password(password), "USER", preferred_language),
    )
    conn.commit()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone()
    conn.close()

    token = issue_token(uid)
    return jsonify({"token": token, "user": public_user(user)}), 201


@bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    conn = get_connection()
    user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()

    if not user or not verify_password(password, user["password_hash"]):
        return jsonify({"error": "Invalid email or password."}), 401

    token = issue_token(user["id"])
    return jsonify({"token": token, "user": public_user(user)})


@bp.get("/me")
@require_auth
def me():
    return jsonify({"user": public_user(g.user)})


@bp.put("/me")
@require_auth
def update_me():
    data = request.get_json(silent=True) or {}
    fields = []
    values = []
    if "name" in data and (data["name"] or "").strip():
        fields.append("name = ?")
        values.append(data["name"].strip())
    if "preferredLanguage" in data:
        fields.append("preferred_language = ?")
        values.append(data["preferredLanguage"])
    if not fields:
        return jsonify({"user": public_user(g.user)})
    values.append(g.user["id"])
    conn = get_connection()
    conn.execute(f"UPDATE users SET {', '.join(fields)} WHERE id = ?", values)
    conn.commit()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (g.user["id"],)).fetchone()
    conn.close()
    return jsonify({"user": public_user(user)})
