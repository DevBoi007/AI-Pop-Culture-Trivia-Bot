"""
SQLite database operations for the AI Culture Trivia Chatbot.
Handles user management, session tracking, answer history, leaderboard, and daily challenges.
"""

import sqlite3
import json
from datetime import datetime, date
from contextlib import contextmanager

from config import DATABASE_PATH


# ─── Connection Manager ──────────────────────────────────

@contextmanager
def get_connection():
    """Context manager for database connections."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ─── Initialization ──────────────────────────────────────

def init_db():
    """Create all tables if they don't exist."""
    with get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                mode TEXT NOT NULL,
                score INTEGER DEFAULT 0,
                total_questions INTEGER DEFAULT 0,
                correct_answers INTEGER DEFAULT 0,
                accuracy REAL DEFAULT 0.0,
                difficulty_reached INTEGER DEFAULT 1,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ended_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS answers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                question_text TEXT NOT NULL,
                user_answer TEXT,
                correct_answer TEXT NOT NULL,
                is_correct INTEGER DEFAULT 0,
                score_awarded INTEGER DEFAULT 0,
                difficulty INTEGER DEFAULT 1,
                topic TEXT,
                time_taken REAL,
                hints_used INTEGER DEFAULT 0,
                answered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions(id)
            );

            CREATE TABLE IF NOT EXISTS daily_challenges (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                challenge_date DATE UNIQUE NOT NULL,
                theme TEXT,
                questions_json TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS daily_scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                challenge_date DATE NOT NULL,
                score INTEGER DEFAULT 0,
                total_correct INTEGER DEFAULT 0,
                completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                UNIQUE(user_id, challenge_date)
            );
        """)


# ─── User Operations ─────────────────────────────────────

def create_user(username: str) -> int:
    """Create a new user. Returns user ID."""
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO users (username) VALUES (?)",
            (username.strip(),)
        )
        return cursor.lastrowid


def get_user(username: str) -> dict | None:
    """Get user by username."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE username = ?",
            (username.strip(),)
        ).fetchone()
        return dict(row) if row else None


def get_or_create_user(username: str) -> dict:
    """Get existing user or create a new one."""
    user = get_user(username)
    if user is None:
        user_id = create_user(username)
        user = {"id": user_id, "username": username.strip()}
    return user


# ─── Session Operations ──────────────────────────────────

def create_session(user_id: int, mode: str) -> int:
    """Create a new quiz session. Returns session ID."""
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO sessions (user_id, mode) VALUES (?, ?)",
            (user_id, mode)
        )
        return cursor.lastrowid


def update_session(session_id: int, score: int, total_questions: int,
                   correct_answers: int, difficulty_reached: int):
    """Update session with final results."""
    accuracy = (correct_answers / total_questions * 100) if total_questions > 0 else 0
    with get_connection() as conn:
        conn.execute(
            """UPDATE sessions 
               SET score = ?, total_questions = ?, correct_answers = ?,
                   accuracy = ?, difficulty_reached = ?, ended_at = ?
               WHERE id = ?""",
            (score, total_questions, correct_answers, round(accuracy, 1),
             difficulty_reached, datetime.now().isoformat(), session_id)
        )


# ─── Answer Operations ───────────────────────────────────

def save_answer(session_id: int, question_text: str, user_answer: str,
                correct_answer: str, is_correct: bool, score_awarded: int,
                difficulty: int, topic: str, time_taken: float = None,
                hints_used: int = 0):
    """Save a single answer record."""
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO answers 
               (session_id, question_text, user_answer, correct_answer,
                is_correct, score_awarded, difficulty, topic, time_taken, hints_used)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (session_id, question_text, user_answer, correct_answer,
             int(is_correct), score_awarded, difficulty, topic, time_taken, hints_used)
        )


# ─── Statistics ───────────────────────────────────────────

def get_user_stats(user_id: int) -> dict:
    """Get aggregated stats for a user."""
    with get_connection() as conn:
        # Overall stats
        row = conn.execute(
            """SELECT 
                COUNT(*) as total_sessions,
                COALESCE(SUM(score), 0) as total_score,
                COALESCE(AVG(accuracy), 0) as avg_accuracy,
                COALESCE(MAX(score), 0) as best_score,
                COALESCE(MAX(difficulty_reached), 1) as max_difficulty,
                COALESCE(SUM(total_questions), 0) as total_questions_answered,
                COALESCE(SUM(correct_answers), 0) as total_correct
               FROM sessions WHERE user_id = ? AND ended_at IS NOT NULL""",
            (user_id,)
        ).fetchone()

        stats = dict(row) if row else {}

        # Topic performance
        topics = conn.execute(
            """SELECT topic, 
                COUNT(*) as total,
                SUM(is_correct) as correct,
                ROUND(AVG(is_correct) * 100, 1) as accuracy
               FROM answers a
               JOIN sessions s ON a.session_id = s.id
               WHERE s.user_id = ?
               GROUP BY topic""",
            (user_id,)
        ).fetchall()
        stats["topic_performance"] = [dict(t) for t in topics]

        # Recent sessions for progress chart
        recent = conn.execute(
            """SELECT score, accuracy, difficulty_reached, mode, ended_at
               FROM sessions 
               WHERE user_id = ? AND ended_at IS NOT NULL
               ORDER BY ended_at DESC LIMIT 20""",
            (user_id,)
        ).fetchall()
        stats["recent_sessions"] = [dict(r) for r in recent]

        return stats


def get_user_topic_preferences(user_id: int) -> dict:
    """Get topic preferences based on correct answer rates."""
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT topic,
                COUNT(*) as total,
                SUM(is_correct) as correct,
                ROUND(AVG(is_correct) * 100, 1) as accuracy
               FROM answers a
               JOIN sessions s ON a.session_id = s.id
               WHERE s.user_id = ?
               GROUP BY topic
               ORDER BY accuracy DESC""",
            (user_id,)
        ).fetchall()
        return {row["topic"]: {"total": row["total"], "correct": row["correct"],
                               "accuracy": row["accuracy"]} for row in rows}


# ─── Leaderboard ─────────────────────────────────────────

def get_leaderboard(mode: str = None, limit: int = 10) -> list:
    """Get top scores, optionally filtered by mode."""
    with get_connection() as conn:
        if mode:
            rows = conn.execute(
                """SELECT u.username, s.score, s.accuracy, s.mode, 
                          s.difficulty_reached, s.ended_at
                   FROM sessions s
                   JOIN users u ON s.user_id = u.id
                   WHERE s.mode = ? AND s.ended_at IS NOT NULL
                   ORDER BY s.score DESC
                   LIMIT ?""",
                (mode, limit)
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT u.username, s.score, s.accuracy, s.mode,
                          s.difficulty_reached, s.ended_at
                   FROM sessions s
                   JOIN users u ON s.user_id = u.id
                   WHERE s.ended_at IS NOT NULL
                   ORDER BY s.score DESC
                   LIMIT ?""",
                (limit,)
            ).fetchall()
        return [dict(r) for r in rows]


def get_daily_leaderboard(challenge_date: str = None, limit: int = 10) -> list:
    """Get daily challenge leaderboard."""
    if challenge_date is None:
        challenge_date = date.today().isoformat()
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT u.username, d.score, d.total_correct, d.completed_at
               FROM daily_scores d
               JOIN users u ON d.user_id = u.id
               WHERE d.challenge_date = ?
               ORDER BY d.score DESC
               LIMIT ?""",
            (challenge_date, limit)
        ).fetchall()
        return [dict(r) for r in rows]


# ─── Daily Challenge ─────────────────────────────────────

def save_daily_challenge(challenge_date: str, theme: str, questions: list):
    """Save a daily challenge."""
    with get_connection() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO daily_challenges (challenge_date, theme, questions_json)
               VALUES (?, ?, ?)""",
            (challenge_date, theme, json.dumps(questions))
        )


def get_daily_challenge(challenge_date: str = None) -> dict | None:
    """Get today's daily challenge."""
    if challenge_date is None:
        challenge_date = date.today().isoformat()
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM daily_challenges WHERE challenge_date = ?",
            (challenge_date,)
        ).fetchone()
        if row:
            result = dict(row)
            result["questions"] = json.loads(result["questions_json"])
            return result
        return None


def save_daily_score(user_id: int, challenge_date: str, score: int, total_correct: int):
    """Save a user's daily challenge score."""
    with get_connection() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO daily_scores 
               (user_id, challenge_date, score, total_correct)
               VALUES (?, ?, ?, ?)""",
            (user_id, challenge_date, score, total_correct)
        )


def has_completed_daily(user_id: int, challenge_date: str = None) -> bool:
    """Check if user already completed today's daily challenge."""
    if challenge_date is None:
        challenge_date = date.today().isoformat()
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id FROM daily_scores WHERE user_id = ? AND challenge_date = ?",
            (user_id, challenge_date)
        ).fetchone()
        return row is not None
