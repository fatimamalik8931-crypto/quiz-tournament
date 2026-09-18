-- Quiz Tournament — database schema (SQLite)
-- Portable, plain SQL: the same statements work against PostgreSQL/MySQL
-- with trivial type tweaks (TEXT->UUID, INTEGER PK -> SERIAL, etc.) if you
-- outgrow SQLite later.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    id                 TEXT PRIMARY KEY,
    name               TEXT NOT NULL,
    email              TEXT NOT NULL UNIQUE,
    password_hash      TEXT NOT NULL,
    role               TEXT NOT NULL DEFAULT 'USER',      -- USER | ADMIN
    preferred_language TEXT NOT NULL DEFAULT 'en',
    total_points       INTEGER NOT NULL DEFAULT 0,
    created_at         TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

CREATE TABLE IF NOT EXISTS categories (
    id          TEXT PRIMARY KEY,
    key         TEXT NOT NULL UNIQUE,   -- education | technology | general_knowledge | sports | entertainment | science_nature
    icon        TEXT NOT NULL,          -- keyword the frontend maps to an inline SVG icon
    color_from  TEXT NOT NULL DEFAULT '#7C3AED',
    color_to    TEXT NOT NULL DEFAULT '#C026D3',
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

CREATE TABLE IF NOT EXISTS category_translations (
    id          TEXT PRIMARY KEY,
    category_id TEXT NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
    language    TEXT NOT NULL,          -- 'en' | 'ur' | ...
    name        TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    UNIQUE(category_id, language)
);

CREATE TABLE IF NOT EXISTS questions (
    id                 TEXT PRIMARY KEY,
    category_id        TEXT NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
    difficulty         TEXT NOT NULL DEFAULT 'medium',   -- easy | medium | hard
    points             INTEGER NOT NULL DEFAULT 10,
    time_limit_seconds INTEGER NOT NULL DEFAULT 20,
    correct_index      INTEGER NOT NULL,                 -- 0-3, same across every translation's options
    created_at         TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    updated_at         TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

CREATE TABLE IF NOT EXISTS question_translations (
    id            TEXT PRIMARY KEY,
    question_id   TEXT NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    language      TEXT NOT NULL,
    text          TEXT NOT NULL,
    options_json  TEXT NOT NULL,        -- JSON array of exactly 4 option strings, same order as correct_index
    UNIQUE(question_id, language)
);

CREATE TABLE IF NOT EXISTS tournaments (
    id               TEXT PRIMARY KEY,
    name             TEXT NOT NULL,
    category_id      TEXT REFERENCES categories(id) ON DELETE SET NULL,  -- NULL = mixed categories
    start_time       TEXT NOT NULL,
    duration_minutes INTEGER NOT NULL DEFAULT 10,
    per_question_secs INTEGER NOT NULL DEFAULT 20,
    status           TEXT NOT NULL DEFAULT 'SCHEDULED',    -- SCHEDULED | LIVE | COMPLETED | CANCELLED
    created_at       TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

CREATE TABLE IF NOT EXISTS tournament_questions (
    id            TEXT PRIMARY KEY,
    tournament_id TEXT NOT NULL REFERENCES tournaments(id) ON DELETE CASCADE,
    question_id   TEXT NOT NULL REFERENCES questions(id),
    position      INTEGER NOT NULL,
    UNIQUE(tournament_id, position)
);

CREATE TABLE IF NOT EXISTS tournament_participants (
    id            TEXT PRIMARY KEY,
    tournament_id TEXT NOT NULL REFERENCES tournaments(id) ON DELETE CASCADE,
    user_id       TEXT NOT NULL REFERENCES users(id),
    score         INTEGER NOT NULL DEFAULT 0,
    correct_count INTEGER NOT NULL DEFAULT 0,
    total_time_ms INTEGER NOT NULL DEFAULT 0,
    rank          INTEGER,
    joined_at     TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    finished_at   TEXT,
    UNIQUE(tournament_id, user_id)
);

CREATE TABLE IF NOT EXISTS tournament_answers (
    id             TEXT PRIMARY KEY,
    participant_id TEXT NOT NULL REFERENCES tournament_participants(id) ON DELETE CASCADE,
    question_id    TEXT NOT NULL REFERENCES questions(id),
    selected_index INTEGER,
    correct        INTEGER NOT NULL DEFAULT 0,
    time_ms        INTEGER NOT NULL DEFAULT 0,
    UNIQUE(participant_id, question_id)
);

CREATE TABLE IF NOT EXISTS quiz_attempts (
    id              TEXT PRIMARY KEY,
    user_id         TEXT NOT NULL REFERENCES users(id),
    category_id     TEXT NOT NULL REFERENCES categories(id),
    language        TEXT NOT NULL DEFAULT 'en',
    score           INTEGER NOT NULL DEFAULT 0,
    correct_count   INTEGER NOT NULL DEFAULT 0,
    total_questions INTEGER NOT NULL DEFAULT 0,
    created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

CREATE TABLE IF NOT EXISTS quiz_answers (
    id             TEXT PRIMARY KEY,
    attempt_id     TEXT NOT NULL REFERENCES quiz_attempts(id) ON DELETE CASCADE,
    question_id    TEXT NOT NULL REFERENCES questions(id),
    selected_index INTEGER,
    correct        INTEGER NOT NULL DEFAULT 0,
    time_ms        INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS badges (
    id          TEXT PRIMARY KEY,
    key         TEXT NOT NULL UNIQUE,
    name        TEXT NOT NULL,
    description TEXT NOT NULL,
    icon        TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS user_badges (
    id        TEXT PRIMARY KEY,
    user_id   TEXT NOT NULL REFERENCES users(id),
    badge_id  TEXT NOT NULL REFERENCES badges(id),
    earned_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    UNIQUE(user_id, badge_id)
);

CREATE INDEX IF NOT EXISTS idx_questions_category ON questions(category_id);
CREATE INDEX IF NOT EXISTS idx_quiz_attempts_user ON quiz_attempts(user_id);
CREATE INDEX IF NOT EXISTS idx_tournament_participants_tournament ON tournament_participants(tournament_id);
