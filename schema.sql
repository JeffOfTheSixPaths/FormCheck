-- ==============================================================================
-- FormCheck Database Schema (SQLite / SQL Standard DDL)
-- 
-- Tables:
--   1. users            - User accounts, credentials, and profile metadata
--   2. workout_sessions - Exercise tracking logs (clean/flawed reps, form scores)
--   3. user_settings    - Per-user preferences (camera selection, confidence thresholds)
-- ==============================================================================

-- Enable Foreign Key constraint enforcement in SQLite
PRAGMA foreign_keys = ON;

-- ------------------------------------------------------------------------------
-- 1. USERS TABLE
-- Stores user authentication credentials securely.
-- Passwords must NEVER be stored in plain text.
-- password_hash stores PBKDF2-HMAC-SHA256 (600,000 iterations).
-- salt stores a cryptographically secure random 16-byte hex value per user.
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT NOT NULL COLLATE NOCASE,
    email         TEXT NOT NULL COLLATE NOCASE,
    password_hash TEXT NOT NULL,
    salt          TEXT NOT NULL,
    full_name     TEXT,
    is_active     INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    created_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now')),
    updated_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now')),
    last_login_at TEXT
);

-- Case-insensitive unique indexes for fast lookups during login
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- ------------------------------------------------------------------------------
-- 2. WORKOUT_SESSIONS TABLE
-- Stores completed workout reps, form scores, and durations for each user.
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS workout_sessions (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id          INTEGER NOT NULL,
    exercise_name    TEXT NOT NULL,
    clean_reps       INTEGER NOT NULL DEFAULT 0 CHECK (clean_reps >= 0),
    flawed_reps      INTEGER NOT NULL DEFAULT 0 CHECK (flawed_reps >= 0),
    total_reps       INTEGER NOT NULL DEFAULT 0 CHECK (total_reps >= 0),
    avg_form_score   REAL NOT NULL DEFAULT 0.0 CHECK (avg_form_score >= 0.0 AND avg_form_score <= 100.0),
    duration_seconds INTEGER NOT NULL DEFAULT 0 CHECK (duration_seconds >= 0),
    created_at       TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now')),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON workout_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_exercise ON workout_sessions(exercise_name);
CREATE INDEX IF NOT EXISTS idx_sessions_created_at ON workout_sessions(created_at);

-- ------------------------------------------------------------------------------
-- 3. USER_SETTINGS TABLE
-- Stores user-specific hardware and preference defaults.
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS user_settings (
    user_id          INTEGER PRIMARY KEY,
    preferred_camera INTEGER NOT NULL DEFAULT 0,
    min_confidence   REAL NOT NULL DEFAULT 0.5,
    remember_login   INTEGER NOT NULL DEFAULT 0 CHECK (remember_login IN (0, 1)),
    updated_at       TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now')),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- ------------------------------------------------------------------------------
-- 4. UPLOADED_VIDEOS TABLE
-- Stores uploaded professional athlete archive and personal user videos.
-- category: 'pro' (professional archive), 'personal' (user-uploaded), or 'both'
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS uploaded_videos (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id           INTEGER,
    title             TEXT NOT NULL,
    category          TEXT NOT NULL CHECK (category IN ('pro', 'personal', 'both')),
    sport             TEXT NOT NULL DEFAULT 'General',
    file_path         TEXT NOT NULL,
    thumbnail_path    TEXT,
    fps               REAL DEFAULT 30.0,
    total_frames      INTEGER DEFAULT 0,
    duration_seconds  REAL DEFAULT 0.0,
    resolution        TEXT DEFAULT '1920x1080',
    description       TEXT,
    uploaded_at       TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now')),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_videos_category ON uploaded_videos(category);
CREATE INDEX IF NOT EXISTS idx_videos_user_id ON uploaded_videos(user_id);
CREATE INDEX IF NOT EXISTS idx_videos_sport ON uploaded_videos(sport);

-- ------------------------------------------------------------------------------
-- 5. TRIGGERS
-- Automatically update the updated_at timestamp on row modification.
-- ------------------------------------------------------------------------------
CREATE TRIGGER IF NOT EXISTS trg_users_updated_at
AFTER UPDATE ON users
FOR EACH ROW
BEGIN
    UPDATE users 
    SET updated_at = strftime('%Y-%m-%d %H:%M:%S', 'now') 
    WHERE id = OLD.id;
END;

CREATE TRIGGER IF NOT EXISTS trg_user_settings_updated_at
AFTER UPDATE ON user_settings
FOR EACH ROW
BEGIN
    UPDATE user_settings 
    SET updated_at = strftime('%Y-%m-%d %H:%M:%S', 'now') 
    WHERE user_id = OLD.user_id;
END;
