"""Password hashing + JWT auth helpers, and route decorators."""
import datetime
import os
from functools import wraps

import jwt
from flask import request, jsonify, g
from werkzeug.security import generate_password_hash, check_password_hash

from db import get_connection

JWT_SECRET = os.environ.get("JWT_SECRET", "quiz-tournament-dev-secret-change-me")
JWT_ALGO = "HS256"
JWT_EXPIRES_HOURS = 24 * 7  # one week


def hash_password(plain):
    return generate_password_hash(plain)


def verify_password(plain, hashed):
    return check_password_hash(hashed, plain)


def issue_token(user_id):
    payload = {
        "sub": user_id,
        "iat": datetime.datetime.utcnow(),
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=JWT_EXPIRES_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)


def decode_token(token):
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])
    except jwt.PyJWTError:
        return None


def get_bearer_token():
    header = request.headers.get("Authorization", "")
    if header.startswith("Bearer "):
        return header[7:]
    return None


def load_current_user():
    """Populate g.user from the Authorization header, or None."""
    g.user = None
    token = get_bearer_token()
    if not token:
        return
    payload = decode_token(token)
    if not payload:
        return
    conn = get_connection()
    row = conn.execute("SELECT * FROM users WHERE id = ?", (payload["sub"],)).fetchone()
    conn.close()
    if row:
        g.user = dict(row)


def require_auth(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not getattr(g, "user", None):
            return jsonify({"error": "Authentication required"}), 401
        return fn(*args, **kwargs)
    return wrapper


def require_admin(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not getattr(g, "user", None):
            return jsonify({"error": "Authentication required"}), 401
        if g.user.get("role") != "ADMIN":
            return jsonify({"error": "Admin access required"}), 403
        return fn(*args, **kwargs)
    return wrapper


def public_user(user_row):
    """Strip the password hash before sending a user object to the client."""
    if not user_row:
        return None
    d = dict(user_row)
    d.pop("password_hash", None)
    return d
