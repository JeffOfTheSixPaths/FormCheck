"""Test suite for FormCheck SQLite schema, authentication, and workout tracking."""

import os
import sys
import tempfile
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services.db import DatabaseManager, hash_password, verify_password


def test_auth_and_schema():
    with tempfile.TemporaryDirectory() as tmpdir:
        test_db_path = Path(tmpdir) / "test_formcheck.db"
        manager = DatabaseManager(db_path=test_db_path)

        # 1. Verify schema tables exist
        with manager.connection_scope() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = {row["name"] for row in cursor.fetchall()}
            assert "users" in tables, "users table missing"
            assert "workout_sessions" in tables, "workout_sessions table missing"
            assert "user_settings" in tables, "user_settings table missing"

        # 2. Test registration
        success, msg, user = manager.register_user(
            username="testuser",
            email="test@example.com",
            password="securePassword123",
            full_name="Test Runner",
        )
        assert success, f"Registration failed: {msg}"
        assert user is not None
        assert user["username"] == "testuser"
        user_id = user["id"]

        # Duplicate registration rejection
        dup_success, dup_msg, _ = manager.register_user(
            username="testuser",
            email="another@example.com",
            password="differentPassword",
        )
        assert not dup_success, "Duplicate username allowed!"
        assert "already taken" in dup_msg.lower()

        # 3. Test authentication
        # Valid login with username
        auth_success, auth_msg, auth_user = manager.authenticate_user("testuser", "securePassword123")
        assert auth_success, f"Username auth failed: {auth_msg}"
        assert auth_user["id"] == user_id

        # Valid login with email
        auth_email_success, _, _ = manager.authenticate_user("test@example.com", "securePassword123")
        assert auth_email_success, "Email auth failed"

        # Invalid password
        fail_success, fail_msg, _ = manager.authenticate_user("testuser", "wrongPassword")
        assert not fail_success, "Invalid password was accepted!"
        assert "invalid" in fail_msg.lower()

        # Nonexistent user
        non_success, _, _ = manager.authenticate_user("ghost", "password")
        assert not non_success

        # 4. Test workout session logging
        s1 = manager.log_workout_session(
            user_id=user_id,
            exercise_name="Squat",
            clean_reps=10,
            flawed_reps=2,
            avg_form_score=85.5,
            duration_seconds=45,
        )
        assert s1 is not None and s1 > 0

        s2 = manager.log_workout_session(
            user_id=user_id,
            exercise_name="Pushup",
            clean_reps=15,
            flawed_reps=0,
            avg_form_score=98.0,
            duration_seconds=30,
        )
        assert s2 is not None and s2 > s1

        # 5. Test history retrieval and stats calculation
        history = manager.get_user_workout_history(user_id)
        assert len(history) == 2
        assert history[0]["exercise_name"] == "Pushup"  # newest first
        assert history[1]["exercise_name"] == "Squat"

        stats = manager.get_user_summary_stats(user_id)
        assert stats["total_sessions"] == 2
        assert stats["total_clean_reps"] == 25
        assert stats["total_flawed_reps"] == 2
        assert stats["grand_total_reps"] == 27
        assert 90.0 < stats["overall_avg_score"] < 95.0

        # Close any lingering references so Windows allows tempdir removal
        del conn
        del manager
        import gc
        gc.collect()

        print("ALL TESTS PASSED SUCCESSFULLY! Schema, hashing, authentication, and workout tracking are verified.")


if __name__ == "__main__":
    test_auth_and_schema()
