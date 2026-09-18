"""Quiz Tournament — Flask application entrypoint.

Serves the JSON API under /api/* and the single-page frontend (static files
+ templates/index.html) for everything else, so the whole app runs as one
process on one port with no CORS configuration needed.
"""
import os

from flask import Flask, render_template

from db import init_db
from auth_utils import load_current_user

from api.auth import bp as auth_bp
from api.categories import bp as categories_bp
from api.quiz import bp as quiz_bp
from api.tournaments import bp as tournaments_bp
from api.leaderboard import bp as leaderboard_bp
from api.users import bp as users_bp
from api.admin import bp as admin_bp

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(
    __name__,
    static_folder=os.path.join(BASE_DIR, "static"),
    template_folder=os.path.join(BASE_DIR, "templates"),
)

app.register_blueprint(auth_bp)
app.register_blueprint(categories_bp)
app.register_blueprint(quiz_bp)
app.register_blueprint(tournaments_bp)
app.register_blueprint(leaderboard_bp)
app.register_blueprint(users_bp)
app.register_blueprint(admin_bp)


@app.before_request
def _attach_user():
    load_current_user()


@app.after_request
def _no_cache_api(resp):
    # Keep API responses (and the SSE stream) from being cached by the browser.
    return resp


@app.route("/")
@app.route("/<path:_client_route>")
def index(_client_route=None):
    """Serve the SPA shell for every non-API route so client-side routing
    (e.g. /tournaments/<id>) works on a hard refresh."""
    return render_template("index.html")


if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True, threaded=True)
