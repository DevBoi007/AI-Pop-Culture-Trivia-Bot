"""
AI Engine for the Culture Trivia Chatbot.
Uses Google Gemini (google-genai SDK) for question generation, answer evaluation,
hints, and explanations. Falls back to the local JSON dataset when unavailable.
"""

import json
import random
from pathlib import Path

try:
    from google import genai
    from google.genai import types
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

from config import GEMINI_MODEL, GENERATION_CONFIG, TOPICS, DAILY_CHALLENGE_QUESTIONS


# ─── State ────────────────────────────────────────────────

_client = None
_api_ready = False
_fallback_questions = None


# ─── Initialization ──────────────────────────────────────

def init_gemini(api_key: str) -> tuple[bool, str]:
    """
    Initialize the Gemini client with the new google-genai SDK.
    Returns (success: bool, error_message: str).
    Does NOT make a live API call — validates key format and sets up the client.
    """
    global _client, _api_ready

    if not GEMINI_AVAILABLE:
        _api_ready = False
        return False, "google-genai package not installed. Run: pip install google-genai"

    if not api_key or not api_key.strip():
        _api_ready = False
        return False, "API key is empty."

    api_key = api_key.strip()

    # Gemini keys always start with 'AIza'
    if not api_key.startswith("AIza"):
        _api_ready = False
        return False, "Invalid API key format. Gemini keys start with 'AIza'."

    try:
        _client = genai.Client(api_key=api_key)
        _api_ready = True
        return True, ""
    except Exception as e:
        err = str(e)
        print(f"Gemini init failed: {err}")
        _api_ready = False
        return False, err


def test_gemini_connection() -> tuple[bool, str]:
    """Make a real lightweight API call to verify the key works."""
    if not is_ai_ready():
        return False, "AI not initialized."
    try:
        _client.models.generate_content(
            model=GEMINI_MODEL,
            contents="Reply with only the word: OK",
        )
        return True, ""
    except Exception as e:
        global _api_ready
        _api_ready = False
        return False, str(e)


def is_ai_ready() -> bool:
    """Check if the AI engine is ready."""
    return _api_ready and _client is not None


# ─── Fallback Dataset ────────────────────────────────────

def _load_fallback():
    """Load the fallback questions dataset."""
    global _fallback_questions
    if _fallback_questions is not None:
        return _fallback_questions

    data_path = Path(__file__).parent / "data" / "questions.json"
    if data_path.exists():
        with open(data_path, "r", encoding="utf-8") as f:
            _fallback_questions = json.load(f)
    else:
        _fallback_questions = []
    return _fallback_questions


def _get_fallback_question(topic: str = None, difficulty: int = 2,
                           asked_questions: list = None) -> dict | None:
    """Get a random question from the fallback dataset."""
    questions = _load_fallback()
    if not questions:
        return None

    asked = set(asked_questions or [])

    # Filter by topic and difficulty range
    candidates = [
        q for q in questions
        if (topic is None or q.get("topic", "").lower() == topic.lower())
        and abs(q.get("difficulty", 2) - difficulty) <= 1
        and q.get("question", "") not in asked
    ]

    # Broaden if no candidates
    if not candidates:
        candidates = [q for q in questions if q.get("question", "") not in asked]

    if not candidates:
        candidates = questions  # Reset — all asked

    return random.choice(candidates) if candidates else None


# ─── Helpers ─────────────────────────────────────────────

def _parse_json_response(text: str) -> dict | None:
    """Extract JSON from a Gemini response."""
    text = text.strip()
    # Strip markdown code fences
    if text.startswith("```"):
        lines = text.split("\n")[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start != -1 and end > start:
            try:
                return json.loads(text[start:end])
            except json.JSONDecodeError:
                return None
    return None


def _generate(prompt: str) -> str | None:
    """Send a prompt to Gemini and return response text."""
    if not is_ai_ready():
        return None
    try:
        config = types.GenerateContentConfig(
            temperature=GENERATION_CONFIG["temperature"],
            top_p=GENERATION_CONFIG["top_p"],
            max_output_tokens=GENERATION_CONFIG["max_output_tokens"],
        )
        response = _client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=config,
        )
        return response.text
    except Exception as e:
        print(f"Gemini generate failed: {e}")
        return None


# ─── AI Functions ─────────────────────────────────────────

def generate_question(topic: str = None, difficulty: int = 2,
                      asked_questions: list = None) -> dict | None:
    """
    Generate a trivia question using AI or fallback.
    Returns dict with: question, options, correct_answer, topic, difficulty
    """
    asked = asked_questions or []

    if is_ai_ready():
        chosen_topic = topic or random.choice(TOPICS)
        diff_desc = {1: "very easy", 2: "easy", 3: "medium",
                     4: "hard", 5: "very hard / expert-level"}

        avoid_text = ""
        if asked:
            recent = asked[-8:]
            avoid_text = "\n\nDo NOT repeat any of these questions:\n" + "\n".join(
                f"- {q}" for q in recent
            )

        prompt = f"""Generate a cultural trivia question about {chosen_topic}.
Difficulty: {diff_desc.get(difficulty, 'medium')} (level {difficulty}/5)

The question must be about world cultures: festivals, history, food, geography, or languages.
Make it interesting and educational.{avoid_text}

Respond ONLY with valid JSON — no markdown, no extra text:
{{
    "question": "the trivia question",
    "options": ["option A", "option B", "option C", "option D"],
    "correct_answer": "the correct option (must exactly match one of the options)",
    "topic": "{chosen_topic}",
    "difficulty": {difficulty}
}}"""

        text = _generate(prompt)
        if text:
            result = _parse_json_response(text)
            if result and "question" in result and "correct_answer" in result:
                if "options" not in result or len(result["options"]) < 4:
                    result["options"] = [result["correct_answer"],
                                          "Option B", "Option C", "Option D"]
                    random.shuffle(result["options"])
                result.setdefault("topic", chosen_topic)
                result.setdefault("difficulty", difficulty)
                return result

    # Fallback
    return _get_fallback_question(topic, difficulty, asked)


def evaluate_answer(question: str, user_answer: str,
                    correct_answer: str, options: list = None) -> dict:
    """
    Evaluate the user's answer using AI semantic comparison.
    Returns dict with: is_correct (bool), confidence (0-1), feedback (str)
    """
    if not user_answer or not user_answer.strip():
        return {"is_correct": False, "confidence": 0.0, "feedback": "No answer provided."}

    user_clean = user_answer.strip().lower()
    correct_clean = correct_answer.strip().lower()

    # Exact match
    if user_clean == correct_clean:
        return {"is_correct": True, "confidence": 1.0, "feedback": "Exactly right!"}

    # Option letter check (A/B/C/D)
    if options and user_clean in ["a", "b", "c", "d"]:
        idx = ord(user_clean) - ord("a")
        if idx < len(options):
            is_c = options[idx].strip().lower() == correct_clean
            return {
                "is_correct": is_c,
                "confidence": 1.0 if is_c else 0.0,
                "feedback": "Correct!" if is_c else "Not quite right."
            }

    # AI semantic check
    if is_ai_ready():
        prompt = f"""Evaluate if the user's answer is correct for this trivia question.
Be lenient — accept partial answers, alternate spellings, and paraphrases.

Question: {question}
Correct Answer: {correct_answer}
User's Answer: {user_answer}

Respond ONLY with valid JSON:
{{
    "is_correct": true or false,
    "confidence": 0.0 to 1.0,
    "feedback": "brief one-line feedback"
}}"""
        text = _generate(prompt)
        if text:
            result = _parse_json_response(text)
            if result and "is_correct" in result:
                return {
                    "is_correct": bool(result["is_correct"]),
                    "confidence": float(result.get("confidence", 0.5)),
                    "feedback": result.get("feedback", "")
                }

    # Fallback string match
    is_correct = correct_clean in user_clean or user_clean in correct_clean
    return {
        "is_correct": is_correct,
        "confidence": 0.8 if is_correct else 0.1,
        "feedback": "Correct!" if is_correct else "Not quite right."
    }


def generate_hint(question: str, correct_answer: str, hint_number: int = 1) -> str:
    """Generate a progressive hint for the question."""
    if is_ai_ready():
        strength = "vague and subtle" if hint_number == 1 else "more direct and helpful"
        prompt = f"""Give a {strength} hint for this trivia question.
Do NOT reveal the answer directly.

Question: {question}
Answer: {correct_answer}
Hint number: {hint_number} of 2

Respond with ONLY the hint text, no quotes, under 20 words."""
        text = _generate(prompt)
        if text and len(text.strip()) > 5:
            return text.strip().strip('"')

    # Fallback
    answer = correct_answer.strip()
    if hint_number == 1:
        return f"The answer starts with '{answer[0]}' and has {len(answer)} characters."
    else:
        revealed = answer[:len(answer) // 2]
        return f"The answer begins with '{revealed}...'"


def generate_explanation(question: str, correct_answer: str,
                         user_answer: str, is_correct: bool) -> dict:
    """
    Generate explanation + fun fact after an answer.
    Returns dict with: verdict, explanation, fun_fact
    """
    if is_ai_ready():
        status = "correctly" if is_correct else "incorrectly"
        prompt = f"""The user answered this trivia question {status}.

Question: {question}
Correct Answer: {correct_answer}
User's Answer: {user_answer}

Provide a helpful response with:
1. A brief verdict (1 sentence)
2. A short educational explanation (2-3 sentences)
3. One fun/surprising fact related to the topic

Respond ONLY with valid JSON:
{{
    "verdict": "Correct! / Incorrect — ...",
    "explanation": "educational explanation...",
    "fun_fact": "a surprising fun fact..."
}}"""
        text = _generate(prompt)
        if text:
            result = _parse_json_response(text)
            if result and "explanation" in result:
                return {
                    "verdict": result.get("verdict", ""),
                    "explanation": result.get("explanation", ""),
                    "fun_fact": result.get("fun_fact", ""),
                }

    # Fallback
    verdict = (f"✅ Correct! The answer is {correct_answer}."
               if is_correct else f"❌ Incorrect. The correct answer is {correct_answer}.")
    return {
        "verdict": verdict,
        "explanation": f"The answer to this question is {correct_answer}.",
        "fun_fact": "Every culture has fascinating stories waiting to be discovered!",
    }


def generate_daily_challenge() -> dict | None:
    """Generate a themed daily challenge with multiple questions."""
    if is_ai_ready():
        themes = [
            "Ancient Civilizations", "World Festivals",
            "Street Food Around the World", "Famous Landmarks",
            "Endangered Languages", "Traditional Clothing",
            "Sacred Places", "Cultural Inventions",
            "World Music Traditions", "Marriage Customs",
        ]
        theme = random.choice(themes)

        prompt = f"""Generate a themed cultural trivia challenge about "{theme}".
Create exactly {DAILY_CHALLENGE_QUESTIONS} questions with increasing difficulty (1 to 5).

Respond ONLY with valid JSON:
{{
    "theme": "{theme}",
    "questions": [
        {{
            "question": "trivia question",
            "options": ["A", "B", "C", "D"],
            "correct_answer": "correct option",
            "difficulty": 1,
            "topic": "topic category",
            "explanation": "brief explanation",
            "fun_fact": "interesting fact"
        }}
    ]
}}"""
        text = _generate(prompt)
        if text:
            result = _parse_json_response(text)
            if result and "questions" in result and len(result["questions"]) > 0:
                return result

    # Fallback from dataset
    questions = _load_fallback()
    if questions and len(questions) >= DAILY_CHALLENGE_QUESTIONS:
        selected = random.sample(questions, DAILY_CHALLENGE_QUESTIONS)
        return {"theme": "World Culture Mix", "questions": selected}
    return None
