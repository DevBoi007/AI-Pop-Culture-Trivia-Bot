"""
Quiz logic for the Culture Trivia Chatbot.
Manages quiz sessions, adaptive difficulty, scoring, and topic preferences.
"""

import time
import random

from config import (
    MIN_DIFFICULTY, MAX_DIFFICULTY, DEFAULT_DIFFICULTY,
    DIFFICULTY_UP_STREAK, DIFFICULTY_DOWN_STREAK,
    BASE_POINTS, DIFFICULTY_MULTIPLIER, TIME_BONUS_MAX,
    STREAK_BONUS, HINT_PENALTY, CHALLENGE_TIME_LIMIT,
    MAX_HINTS_PER_QUESTION, TOPICS, GAME_MODES,
)


class AdaptiveDifficulty:
    """Tracks streaks and adjusts difficulty dynamically."""

    def __init__(self, starting_difficulty: int = DEFAULT_DIFFICULTY):
        self.difficulty = starting_difficulty
        self.correct_streak = 0
        self.wrong_streak = 0
        self.max_reached = starting_difficulty

    def record_answer(self, is_correct: bool):
        """Update streaks and adjust difficulty."""
        if is_correct:
            self.correct_streak += 1
            self.wrong_streak = 0
            if self.correct_streak >= DIFFICULTY_UP_STREAK:
                self.difficulty = min(self.difficulty + 1, MAX_DIFFICULTY)
                self.correct_streak = 0
        else:
            self.wrong_streak += 1
            self.correct_streak = 0
            if self.wrong_streak >= DIFFICULTY_DOWN_STREAK:
                self.difficulty = max(self.difficulty - 1, MIN_DIFFICULTY)
                self.wrong_streak = 0

        self.max_reached = max(self.max_reached, self.difficulty)

    def get_difficulty(self) -> int:
        return self.difficulty


class TopicTracker:
    """Tracks user performance per topic and suggests preferred topics."""

    def __init__(self):
        self.topic_stats = {t: {"correct": 0, "total": 0} for t in TOPICS}

    def record(self, topic: str, is_correct: bool):
        """Record a topic answer."""
        if topic in self.topic_stats:
            self.topic_stats[topic]["total"] += 1
            if is_correct:
                self.topic_stats[topic]["correct"] += 1

    def get_preferred_topic(self) -> str:
        """Get a topic weighted by user interest and performance."""
        weights = []
        for topic in TOPICS:
            stats = self.topic_stats[topic]
            if stats["total"] == 0:
                # Untried topics get medium weight — encourage exploration
                weights.append(3.0)
            else:
                accuracy = stats["correct"] / stats["total"]
                # Users enjoy topics they're good at, but also need variety
                # High accuracy = slightly higher weight, low accuracy = still present
                weights.append(1.0 + accuracy * 3.0)

        return random.choices(TOPICS, weights=weights, k=1)[0]


class QuizSession:
    """Manages a single quiz session."""

    def __init__(self, mode: str = "quiz", user_id: int = None):
        self.mode = mode
        self.user_id = user_id
        self.mode_config = GAME_MODES.get(mode, GAME_MODES["quiz"])

        # Scoring
        self.score = 0
        self.questions_answered = 0
        self.correct_answers = 0
        self.current_streak = 0
        self.best_streak = 0

        # Current question state
        self.current_question = None
        self.hints_used = 0
        self.question_start_time = None

        # History
        self.asked_questions = []

        # Adaptive systems
        self.difficulty = AdaptiveDifficulty()
        self.topic_tracker = TopicTracker()

        # Session timing
        self.session_start = time.time()

    @property
    def total_questions(self) -> int:
        """Total questions for this mode (0 = unlimited)."""
        return self.mode_config["total_questions"]

    @property
    def is_timed(self) -> bool:
        """Whether this mode uses a timer."""
        return self.mode_config["timed"]

    @property
    def is_finished(self) -> bool:
        """Check if the session is complete."""
        if self.total_questions == 0:
            return False  # Learning mode — never auto-finishes
        return self.questions_answered >= self.total_questions

    @property
    def accuracy(self) -> float:
        """Current accuracy percentage."""
        if self.questions_answered == 0:
            return 0.0
        return round(self.correct_answers / self.questions_answered * 100, 1)

    @property
    def progress(self) -> float:
        """Progress through the quiz (0.0 to 1.0)."""
        if self.total_questions == 0:
            return 0.0
        return min(self.questions_answered / self.total_questions, 1.0)

    def set_current_question(self, question: dict):
        """Set the current question and start the timer."""
        self.current_question = question
        self.hints_used = 0
        self.question_start_time = time.time()
        self.asked_questions.append(question.get("question", ""))

    def use_hint(self) -> bool:
        """Use a hint. Returns True if a hint is available."""
        if self.hints_used < MAX_HINTS_PER_QUESTION:
            self.hints_used += 1
            return True
        return False

    def get_time_elapsed(self) -> float:
        """Seconds elapsed since question was shown."""
        if self.question_start_time is None:
            return 0.0
        return time.time() - self.question_start_time

    def is_time_up(self) -> bool:
        """Check if time is up (challenge mode only)."""
        if not self.is_timed:
            return False
        return self.get_time_elapsed() > CHALLENGE_TIME_LIMIT

    def calculate_score(self, is_correct: bool, time_taken: float = None) -> int:
        """Calculate score for the current answer."""
        if not is_correct:
            self.current_streak = 0
            return 0

        # Base score × difficulty multiplier
        diff = self.difficulty.get_difficulty()
        points = BASE_POINTS * (1 + (diff - 1) * DIFFICULTY_MULTIPLIER)

        # Time bonus (challenge mode)
        if self.is_timed and time_taken is not None:
            time_ratio = max(0, 1 - (time_taken / CHALLENGE_TIME_LIMIT))
            points += TIME_BONUS_MAX * time_ratio

        # Streak bonus
        self.current_streak += 1
        self.best_streak = max(self.best_streak, self.current_streak)
        if self.current_streak > 1:
            points += STREAK_BONUS * (self.current_streak - 1)

        # Hint penalty
        if self.hints_used > 0:
            points *= (1 - HINT_PENALTY * self.hints_used)

        return max(int(points), 10)  # Minimum 10 points

    def record_answer(self, is_correct: bool, time_taken: float = None) -> int:
        """Record an answer and return the score awarded."""
        points = self.calculate_score(is_correct, time_taken)

        self.score += points
        self.questions_answered += 1
        if is_correct:
            self.correct_answers += 1

        # Update adaptive systems
        self.difficulty.record_answer(is_correct)
        if self.current_question:
            topic = self.current_question.get("topic", "General")
            self.topic_tracker.record(topic, is_correct)

        if not is_correct:
            self.current_streak = 0

        return points

    def get_next_topic(self) -> str:
        """Get the next topic, weighted by user preferences."""
        return self.topic_tracker.get_preferred_topic()

    def get_summary(self) -> dict:
        """Get session summary."""
        elapsed = time.time() - self.session_start
        return {
            "mode": self.mode,
            "score": self.score,
            "questions_answered": self.questions_answered,
            "correct_answers": self.correct_answers,
            "accuracy": self.accuracy,
            "best_streak": self.best_streak,
            "difficulty_reached": self.difficulty.max_reached,
            "time_elapsed": round(elapsed, 1),
            "avg_time_per_question": round(
                elapsed / max(self.questions_answered, 1), 1
            ),
        }
