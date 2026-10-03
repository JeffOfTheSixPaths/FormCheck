"""Database service for FormCheck.

Handles SQLite connection management, secure PBKDF2 password hashing,
authentication, parameterized SQL queries, and workout session logging.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import re
import secrets
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from services.settings import BASE_DIR, SCHEMA_PATH

logger = logging.getLogger(__name__)

# Default database file path
DEFAULT_DB_PATH = BASE_DIR / "formcheck.db"

# Password hashing constants (OWASP recommended standard)
HASH_ALGORITHM = "sha256"
HASH_ITERATIONS = 600_000

# Regex patterns for input validation
USERNAME_REGEX = re.compile(r"^[a-zA-Z0-9_\-\.]{3,30}$")
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


def hash_password(password: str, salt: str) -> str:
    """Computes PBKDF2-HMAC-SHA256 hex digest using 600,000 iterations."""
    derived = hashlib.pbkdf2_hmac(
        HASH_ALGORITHM,
        password.encode("utf-8"),
        salt.encode("utf-8"),
        HASH_ITERATIONS,
    )
    return derived.hex()


def verify_password(password: str, salt: str, expected_hash: str) -> bool:
    """Timing-attack-safe password verification."""
    computed_hash = hash_password(password, salt)
    return hmac.compare_digest(computed_hash, expected_hash)


from contextlib import contextmanager

class DatabaseManager:
    """Manages SQLite database lifecycle, authentication, and workout logs."""

    def __init__(self, db_path: Optional[Path] = None) -> None:
        self.db_path = Path(db_path or DEFAULT_DB_PATH)
        self.init_database()

    @contextmanager
    def connection_scope(self):
        """Context manager that automatically manages transaction and closes connection."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def get_connection(self) -> sqlite3.Connection:
        """Returns a raw SQLite connection with foreign keys and Row factory enabled."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def init_database(self) -> None:
        """Executes the DDL schema if tables do not already exist."""
        try:
            if SCHEMA_PATH.exists():
                with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
                    schema_sql = f.read()
            else:
                raise FileNotFoundError(f"Schema file not found at {SCHEMA_PATH}")

            with self.connection_scope() as conn:
                conn.executescript(schema_sql)
            logger.info("Database initialized successfully at: %s", self.db_path)
        except Exception as e:
            logger.error("Failed to initialize database: %s", e)
            raise

    # --------------------------------------------------------------------------
    # Authentication & User Management
    # --------------------------------------------------------------------------

    def register_user(
        self,
        username: str,
        email: str,
        password: str,
        full_name: Optional[str] = None,
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Registers a new user with salted PBKDF2 password hashing.

        Returns:
            (success: bool, message: str, user_data: Optional[dict])
        """
        username = (username or "").strip()
        email = (email or "").strip().lower()

        # Validation
        if not USERNAME_REGEX.match(username):
            return (
                False,
                "Username must be 3-30 characters (letters, numbers, '.', '_', '-').",
                None,
            )

        if not EMAIL_REGEX.match(email):
            return False, "Please enter a valid email address.", None

        if len(password) < 6:
            return False, "Password must be at least 6 characters long.", None

        salt = secrets.token_hex(16)
        pw_hash = hash_password(password, salt)

        try:
            with self.connection_scope() as conn:
                cursor = conn.cursor()

                # Check for existing username or email
                cursor.execute(
                    "SELECT username, email FROM users WHERE username = ? OR email = ?",
                    (username, email),
                )
                existing = cursor.fetchone()
                if existing:
                    if existing["username"].lower() == username.lower():
                        return False, f"Username '{username}' is already taken.", None
                    if existing["email"].lower() == email.lower():
                        return False, f"An account with email '{email}' already exists.", None

                # Parameterized INSERT query prevents SQL injection
                cursor.execute(
                    """
                    INSERT INTO users (username, email, password_hash, salt, full_name)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (username, email, pw_hash, salt, full_name.strip() if full_name else None),
                )
                user_id = cursor.lastrowid

                # Create default user settings
                cursor.execute(
                    "INSERT INTO user_settings (user_id) VALUES (?)",
                    (user_id,),
                )
                conn.commit()

                # Return clean user dictionary (without salt/hash)
                user_data = {
                    "id": user_id,
                    "username": username,
                    "email": email,
                    "full_name": full_name or "",
                    "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }
                logger.info("User '%s' registered successfully (ID: %d).", username, user_id)
                return True, "Account registered successfully!", user_data

        except sqlite3.IntegrityError as e:
            logger.warning("Registration integrity conflict: %s", e)
            return False, "A user with this username or email already exists.", None
        except Exception as e:
            logger.error("Registration error: %s", e)
            return False, f"Registration failed: {str(e)}", None

    def authenticate_user(
        self,
        identifier: str,
        password: str,
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Authenticates a user by username OR email with password verification.

        Returns:
            (success: bool, message: str, user_data: Optional[dict])
        """
        identifier = (identifier or "").strip()
        if not identifier or not password:
            return False, "Please enter both username/email and password.", None

        try:
            with self.connection_scope() as conn:
                cursor = conn.cursor()

                # Parameterized query to look up user safely
                cursor.execute(
                    """
                    SELECT id, username, email, password_hash, salt, full_name, is_active
                    FROM users
                    WHERE (username = ? OR email = ?)
                    LIMIT 1
                    """,
                    (identifier, identifier.lower()),
                )
                row = cursor.fetchone()

                if not row:
                    return False, "Invalid username or password.", None

                if not row["is_active"]:
                    return False, "This account has been deactivated.", None

                # Verify password using timing-safe comparison
                if not verify_password(password, row["salt"], row["password_hash"]):
                    return False, "Invalid username or password.", None

                # Update last login timestamp
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                cursor.execute(
                    "UPDATE users SET last_login_at = ? WHERE id = ?",
                    (now_str, row["id"]),
                )
                conn.commit()

                user_data = {
                    "id": row["id"],
                    "username": row["username"],
                    "email": row["email"],
                    "full_name": row["full_name"] or "",
                    "last_login_at": now_str,
                }
                logger.info("User '%s' logged in successfully.", row["username"])
                return True, "Login successful!", user_data

        except Exception as e:
            logger.error("Authentication error: %s", e)
            return False, f"Authentication error: {str(e)}", None

    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Retrieves a user profile by primary key."""
        try:
            with self.connection_scope() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT id, username, email, full_name, created_at, last_login_at FROM users WHERE id = ?",
                    (user_id,),
                )
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error("Error fetching user %d: %s", user_id, e)
            return None

    # --------------------------------------------------------------------------
    # Workout Sessions Logging
    # --------------------------------------------------------------------------

    def log_workout_session(
        self,
        user_id: int,
        exercise_name: str,
        clean_reps: int,
        flawed_reps: int,
        avg_form_score: float,
        duration_seconds: int = 0,
    ) -> Optional[int]:
        """Records completed workout repetitions and average form score for a user."""
        try:
            total_reps = max(0, clean_reps) + max(0, flawed_reps)
            clamped_score = max(0.0, min(100.0, float(avg_form_score)))

            with self.connection_scope() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO workout_sessions (
                        user_id, exercise_name, clean_reps, flawed_reps,
                        total_reps, avg_form_score, duration_seconds
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        user_id,
                        exercise_name,
                        clean_reps,
                        flawed_reps,
                        total_reps,
                        round(clamped_score, 1),
                        max(0, duration_seconds),
                    ),
                )
                session_id = cursor.lastrowid
                conn.commit()
                logger.info(
                    "Logged session #%d for user %d: %s (%d reps, %.1f%% score)",
                    session_id,
                    user_id,
                    exercise_name,
                    total_reps,
                    clamped_score,
                )
                return session_id
        except Exception as e:
            logger.error("Failed to log workout session for user %d: %s", user_id, e)
            return None

    def get_user_workout_history(
        self, user_id: int, limit: int = 15
    ) -> List[Dict[str, Any]]:
        """Fetches the latest workout sessions for a given user."""
        try:
            with self.connection_scope() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT id, exercise_name, clean_reps, flawed_reps, total_reps,
                           avg_form_score, duration_seconds, created_at
                    FROM workout_sessions
                    WHERE user_id = ?
                    ORDER BY created_at DESC, id DESC
                    LIMIT ?
                    """,
                    (user_id, limit),
                )
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error("Failed to get workout history for user %d: %s", user_id, e)
            return []

    def get_user_summary_stats(self, user_id: int) -> Dict[str, Any]:
        """Calculates total reps, average score, and total workout sessions."""
        try:
            with self.connection_scope() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT 
                        COUNT(id) as total_sessions,
                        COALESCE(SUM(clean_reps), 0) as total_clean_reps,
                        COALESCE(SUM(flawed_reps), 0) as total_flawed_reps,
                        COALESCE(SUM(total_reps), 0) as grand_total_reps,
                        COALESCE(AVG(avg_form_score), 0.0) as overall_avg_score
                    FROM workout_sessions
                    WHERE user_id = ?
                    """,
                    (user_id,),
                )
                row = cursor.fetchone()
                if row:
                    return {
                        "total_sessions": row["total_sessions"],
                        "total_clean_reps": row["total_clean_reps"],
                        "total_flawed_reps": row["total_flawed_reps"],
                        "grand_total_reps": row["grand_total_reps"],
                        "overall_avg_score": round(row["overall_avg_score"], 1),
                    }
        except Exception as e:
            logger.error("Failed to fetch summary stats for user %d: %s", user_id, e)

        return {
            "total_sessions": 0,
            "total_clean_reps": 0,
            "total_flawed_reps": 0,
            "grand_total_reps": 0,
            "overall_avg_score": 0.0,
        }


# Singleton database instance
db = DatabaseManager()
