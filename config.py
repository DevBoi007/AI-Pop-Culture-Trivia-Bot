"""
Configuration constants for the AI Culture Trivia Chatbot.
"""

# ─── Topics ───────────────────────────────────────────────
TOPICS = ["TV", "Movies", "Music"]

# ─── Difficulty ───────────────────────────────────────────
MIN_DIFFICULTY = 1
MAX_DIFFICULTY = 5
DEFAULT_DIFFICULTY = 2
DIFFICULTY_UP_STREAK = 2      # Correct answers in a row to increase difficulty
DIFFICULTY_DOWN_STREAK = 2    # Wrong answers in a row to decrease difficulty

# ─── Game Modes ───────────────────────────────────────────
GAME_MODES = {
    "quiz": {
        "name": "🎯 Quiz Mode",
        "description": "Classic trivia — 10 questions, scored with adaptive difficulty.",
        "total_questions": 10,
        "timed": False,
    },
    "learning": {
        "name": "📚 Learning Mode",
        "description": "Explore at your pace — detailed explanations, no timer, no pressure.",
        "total_questions": 0,  # Unlimited
        "timed": False,
    },
    "challenge": {
        "name": "⚡ Challenge Mode",
        "description": "Race the clock — 10 questions, 20 seconds each, bonus points for speed!",
        "total_questions": 10,
        "timed": True,
    },
}

# ─── Scoring ──────────────────────────────────────────────
BASE_POINTS = 100
DIFFICULTY_MULTIPLIER = 0.5     # Extra 50% per difficulty level
TIME_BONUS_MAX = 50             # Max bonus points for fast answers
STREAK_BONUS = 25               # Bonus per consecutive correct answer
HINT_PENALTY = 0.5              # 50% score reduction per hint used

# ─── Timer ────────────────────────────────────────────────
CHALLENGE_TIME_LIMIT = 20       # Seconds per question in challenge mode

# ─── Hints ────────────────────────────────────────────────
MAX_HINTS_PER_QUESTION = 2

# ─── Daily Challenge ─────────────────────────────────────
DAILY_CHALLENGE_QUESTIONS = 5

# ─── Sarvam AI ────────────────────────────────────────────
SARVAM_MODEL = "sarvam-105b"
SARVAM_TEMPERATURE = 0.8
SARVAM_TOP_P = 1.0
SARVAM_MAX_TOKENS = 900
SARVAM_WIKI_GROUNDING = True

# ─── Database ─────────────────────────────────────────────
DATABASE_PATH = "trivia.db"

# ─── UI Theme Colors ─────────────────────────────────────
THEME = {
    "primary": "#6C63FF",
    "secondary": "#FF6584",
    "accent": "#00D2FF",
    "success": "#00E676",
    "warning": "#FFD600",
    "error": "#FF5252",
    "bg_dark": "#0E1117",
    "bg_card": "#1A1D29",
    "bg_card_hover": "#252836",
    "text_primary": "#FFFFFF",
    "text_secondary": "#A0A3B1",
    "gradient_1": "linear-gradient(135deg, #6C63FF 0%, #00D2FF 100%)",
    "gradient_2": "linear-gradient(135deg, #FF6584 0%, #FFD600 100%)",
}

# ─── Difficulty Labels ───────────────────────────────────
DIFFICULTY_LABELS = {
    1: ("Beginner", "🟢"),
    2: ("Easy", "🔵"),
    3: ("Medium", "🟡"),
    4: ("Hard", "🟠"),
    5: ("Expert", "🔴"),
}
