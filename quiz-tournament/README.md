# Quiz Tournament

A full online quiz tournament platform: register, pick a category, play solo
at your own pace, or compete live against other players in a scheduled
tournament — with a real leaderboard, badges, an admin panel, and a bilingual
(English / Urdu) interface.

## Why Flask + SQLite + vanilla JS instead of Node/React/Mongo/Socket.io

This was built in a sandboxed environment with no access to npm or PyPI, so
it had to be built entirely from packages that were already installed —
which meant Python/Flask instead of Node/Express, SQLite instead of
Mongo/Postgres, plain JavaScript instead of a bundled React app, and
Server-Sent Events instead of Socket.io for the live tournament updates.
The result is a **real, fully working app** — every feature in the original
spec is implemented and tested end-to-end — that also happens to need
nothing but Python to run: no database server to install, no `npm install`,
no build step, no internet connection required.

If you'd rather run it on Node/Express/Postgres/Socket.io/React instead, the
architecture maps over directly: `schema.sql` is portable SQL (works on
Postgres with trivial type tweaks), each `api/*.py` blueprint is a thin,
already-documented REST layer you can port route-by-route, and the
`static/js/pages/*.js` files show exactly what each screen needs from the
API, which is all you need to rebuild the same UI in React.

## Quick start

```bash
cd quiz-tournament
pip install -r requirements.txt      # just Flask, PyJWT, Werkzeug
python3 seed.py                      # creates the database + demo data
python3 app.py                       # starts the server on port 5000
```

Open **http://localhost:5000** in your browser. That's the whole setup.

Demo accounts (created by `seed.py`):

| Role  | Email              | Password  |
|-------|--------------------|-----------|
| Admin | admin@quiz.local   | admin123  |
| Player| demo@quiz.local    | demo1234  |

To start over with a clean database: `python3 seed.py --fresh`.

## What's implemented

**Accounts** — email + password registration and login (JWT sessions,
bcrypt-grade password hashing via Werkzeug). Social login isn't wired up
(there's nowhere to register OAuth apps in this environment), but the auth
layer is isolated in `auth_utils.py` / `api/auth.py` if you want to add it.

**Multi-language** — English and Urdu throughout the interface (language
switcher in the header, full RTL layout for Urdu) and in the question bank
itself: every seeded question has both an English and an Urdu translation,
and the admin panel lets you add/edit both. Adding a third language means
adding its code to `SUPPORTED_LANGUAGES` in `helpers.py` and its string
table in `static/js/i18n.js`.

**6 categories**: Education, Technology, General Knowledge, Sports,
Entertainment, Science & Nature — 48 hand-written trivia questions seeded
across them (8 each), each with a difficulty, a point value, and a
15–20 second time limit.

**Practice mode** — pick a category, answer at your own pace against a
per-question countdown ring, get instant right/wrong feedback and a score
breakdown, unlock badges, done anytime with no pressure.

**Tournament mode** — an admin schedules a tournament (category, start
time, question count, seconds per question). Everyone who joins sees the
*same* question at the *same* time, computed purely from the clock (start
time + index × seconds-per-question), so it stays in sync with no
background scheduler process needed. Live updates (current question,
participant count, running mini-leaderboard) are pushed to every open tab
over Server-Sent Events (`EventSource` — a plain, dependency-free browser
API for one-way live updates). Ranking is by score first, total answer
time second, so speed breaks ties. When the tournament's time window ends,
results lock in automatically, points are credited to each player's
profile, and the top finisher gets the "Champion" badge.

**Leaderboards** — overall (by total lifetime points) and per-category.

**Profiles** — quiz + tournament history, total points, badges earned
(First Steps, Perfectionist, Quiz Enthusiast, Speed Demon, Champion).

**Admin panel** — dashboard stats, full CRUD on categories and questions
(with per-language text/options), tournament scheduling and cancellation,
and a read-only view of every user's stats.

**Design** — bright gradient theme, mobile-responsive down to phone width,
progress bar + countdown ring during quizzes, and a confetti celebration on
a strong finish or a tournament win.

## Project layout

```
app.py                 Flask app: registers routes, serves the frontend
schema.sql              Database schema (SQLite; portable plain SQL)
seed.py                 Seeds categories, questions, badges, demo accounts
db.py, auth_utils.py, helpers.py, scoring.py    Shared backend utilities
api/                    One Flask Blueprint per resource (REST JSON API)
templates/index.html   Single-page shell
static/css/style.css   All styling
static/js/              Vanilla-JS SPA: router, API client, i18n, pages/
tests/e2e_smoke_test.py Optional Playwright smoke test (see below)
```

## Scoring

A correct answer earns its base point value (10/15/20 for easy/medium/hard)
plus up to a 50% speed bonus for answering quickly — instant = 1.5×
points, using the full time limit = exactly base points. Wrong or
unanswered = 0. Tournament ranking breaks ties by total time spent
answering (faster wins).

## Running the optional smoke test

`tests/e2e_smoke_test.py` drives the whole app in a real headless browser
(registration → quiz → leaderboard → profile → admin panel) and fails if
anything throws a JS error. It needs `playwright` (`pip install playwright
&& playwright install chromium`) and the server running on port 5000:

```bash
python3 app.py &
python3 tests/e2e_smoke_test.py
```

## Notes for production use

This ships with Flask's built-in dev server (`app.run(debug=True)`), which
is fine for local use or a demo but not for the public internet. For real
deployment: run it behind a WSGI server (gunicorn/uwsgi), set `debug=False`,
move `JWT_SECRET` out of source into a real environment variable, and if you
outgrow SQLite's single-writer model, point `DATABASE_URL` at Postgres and
swap `db.py`'s sqlite3 calls for a Postgres driver — `schema.sql` was
written to make that swap mechanical.
