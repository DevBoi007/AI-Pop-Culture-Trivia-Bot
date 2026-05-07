"""
AI Engine for the Trivia Chatbot.
Uses SarvamAI (sarvamai SDK) for question generation, answer evaluation,
hints, and explanations. Falls back to local JSON dataset when unavailable.
"""

import json
import random
from pathlib import Path

try:
    from sarvamai import SarvamAI
    SARVAM_AVAILABLE = True
except ImportError:
    SARVAM_AVAILABLE = False

from config import (
    TOPICS,
    DAILY_CHALLENGE_QUESTIONS,
    SARVAM_MODEL,
    SARVAM_TEMPERATURE,
    SARVAM_TOP_P,
    SARVAM_MAX_TOKENS,
    SARVAM_WIKI_GROUNDING,
)

# ─── State ────────────────────────────────────────────────
_client = None
_api_ready = False
_fallback_questions = None


# ─── Initialization ──────────────────────────────────────
def init_gemini(api_key: str) -> tuple[bool, str]:
    """
    Backwards-compatible name: your UI calls init_gemini().
    Internally this initializes SarvamAI using the API subscription key.
    """
    global _client, _api_ready

    if not SARVAM_AVAILABLE:
        _api_ready = False
        return False, "sarvamai package not installed. Run: pip install sarvamai"

    if not api_key or not api_key.strip():
        _api_ready = False
        return False, "API key is empty."

    try:
        _client = SarvamAI(api_subscription_key=api_key.strip())
        _api_ready = True
        return True, ""
    except Exception as e:
        _client = None
        _api_ready = False
        return False, str(e)


def test_gemini_connection() -> tuple[bool, str]:
    """Backwards-compatible name. Makes a lightweight Sarvam call."""
    if not is_ai_ready():
        return False, "AI not initialized."

    try:
        text = _generate(
            messages=[{"role": "user", "content": "Reply with only the word: OK"}],
            temperature=0.0,
            top_p=1.0,
            max_tokens=10,
            wiki_grounding=False,
        )
        ok = (text or "").strip().upper() == "OK"
        return (ok, "" if ok else f"Unexpected reply: {text!r}")
    except Exception as e:
        global _api_ready
        _api_ready = False
        return False, str(e)


def is_ai_ready() -> bool:
    return _api_ready and _client is not None


# ─── Fallback Dataset ────────────────────────────────────
def _load_fallback():
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
    questions = _load_fallback()
    if not questions:
        return None

    asked = set(asked_questions or [])

    candidates = [
        q for q in questions
        if (topic is None or q.get("topic", "").lower() == topic.lower())
        and abs(q.get("difficulty", 2) - difficulty) <= 1
        and q.get("question", "") not in asked
    ]

    if not candidates:
        candidates = [q for q in questions if q.get("question", "") not in asked]

    if not candidates:
        candidates = questions

    return random.choice(candidates) if candidates else None


# ─── Helpers ─────────────────────────────────────────────
def _parse_json_response(text: str) -> dict | None:
    text = (text or "").strip()

    # Strip markdown code fences
    if text.startswith("```"):
        lines = text.split("\n")[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()

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


def _generate(
    messages: list[dict],
    temperature: float = SARVAM_TEMPERATURE,
    top_p: float = SARVAM_TOP_P,
    max_tokens: int = SARVAM_MAX_TOKENS,
    wiki_grounding: bool = SARVAM_WIKI_GROUNDING,
) -> str | None:
    """
    Send chat messages to SarvamAI and return assistant content text.
    """
    if not is_ai_ready():
        return None

    resp = _client.chat.completions(
        model=SARVAM_MODEL,
        messages=messages,
        temperature=temperature,
        top_p=top_p,
        max_tokens=max_tokens,
        wiki_grounding=wiki_grounding,
        stream=False,
        # reasoning_effort="medium",  # optional if you want it on
    )

    # Support both dict-like and object-like SDK responses
    try:
        return resp["choices"][0]["message"]["content"]
    except Exception:
        try:
            return resp.choices[0].message.content
        except Exception:
            return None


# ─── AI Functions ─────────────────────────────────────────
def generate_question(topic: str = None, difficulty: int = 2,
                      asked_questions: list = None) -> dict | None:
    asked = asked_questions or []

    if is_ai_ready():
        chosen_topic = topic or random.choice(TOPICS)
        diff_desc = {1: "very easy", 2: "easy", 3: "medium",
                     4: "hard", 5: "very hard / expert-level"}

        avoid_text = ""
        if asked:
            recent = asked[-8:]
            avoid_text = "\nDo NOT repeat any of these questions:\n" + "\n".join(
                f"- {q}" for q in recent
            )

        messages = [
            {"role": "system", "content": (
                "You are a pop culture trivia writer. "
                "Only ask about TV, movies, or music. "
                "Return STRICT JSON only."
            )},
            {"role": "user", "content": f"""
Generate ONE multiple-choice pop culture trivia question.
Category: {chosen_topic}
Difficulty: {diff_desc.get(difficulty, 'medium')} (level {difficulty}/5)

Rules:
- Must be about {chosen_topic} pop culture.
- Avoid ambiguous questions; only ONE option should be clearly correct.
- Provide exactly 4 options.
{avoid_text}

Respond ONLY with valid JSON (no markdown, no extra text):
{{
  "question": "text",
  "options": ["A", "B", "C", "D"],
  "correct_answer": "one of the options exactly",
  "topic": "{chosen_topic}",
  "difficulty": {difficulty},
  "explanation": "1-2 sentences explaining why it's correct",
  "fun_fact": "one short fun fact"
}}
""".strip()}
        ]

        text = _generate(messages=messages, wiki_grounding=True)
        if text:
            result = _parse_json_response(text)
            if result and "question" in result and "correct_answer" in result:
                opts = result.get("options") or []
                if len(opts) != 4:
                    ca = result["correct_answer"]
                    opts = [ca, "Option B", "Option C", "Option D"]
                    random.shuffle(opts)
                    result["options"] = opts

                result.setdefault("topic", chosen_topic)
                result.setdefault("difficulty", difficulty)
                return result

    return _get_fallback_question(topic, difficulty, asked)


def evaluate_answer(question: str, user_answer: str,
                    correct_answer: str, options: list = None) -> dict:
    if not user_answer or not user_answer.strip():
        return {"is_correct": False, "confidence": 0.0, "feedback": "No answer provided."}

    user_clean = user_answer.strip().lower()
    correct_clean = correct_answer.strip().lower()

    if user_clean == correct_clean:
        return {"is_correct": True, "confidence": 1.0, "feedback": "Exactly right!"}

    if options and user_clean in ["a", "b", "c", "d"]:
        idx = ord(user_clean) - ord("a")
        if idx < len(options):
            is_c = options[idx].strip().lower() == correct_clean
            return {"is_correct": is_c, "confidence": 1.0 if is_c else 0.0,
                    "feedback": "Correct!" if is_c else "Not quite right."}

    if is_ai_ready():
        messages = [
            {"role": "system", "content": "You are a grader. Return JSON only."},
            {"role": "user", "content": f"""
Evaluate whether the user's answer should be accepted.
Be lenient for spelling variants and minor paraphrases.

Question: {question}
Correct Answer: {correct_answer}
User Answer: {user_answer}

Return ONLY JSON:
{{
  "is_correct": true/false,
  "confidence": 0.0,
  "feedback": "one short sentence"
}}
""".strip()}
        ]
        text = _generate(messages=messages, temperature=0.2, top_p=1.0, max_tokens=200, wiki_grounding=False)
        result = _parse_json_response(text or "")
        if result and "is_correct" in result:
            return {
                "is_correct": bool(result["is_correct"]),
                "confidence": float(result.get("confidence", 0.5)),
                "feedback": result.get("feedback", ""),
            }

    is_correct = correct_clean in user_clean or user_clean in correct_clean
    return {"is_correct": is_correct, "confidence": 0.8 if is_correct else 0.1,
            "feedback": "Correct!" if is_correct else "Not quite right."}


def generate_hint(question: str, correct_answer: str, hint_number: int = 1) -> str:
    if is_ai_ready():
        strength = "vague and subtle" if hint_number == 1 else "more direct"
        messages = [
            {"role": "system", "content": "Return ONLY the hint text, no quotes."},
            {"role": "user", "content": f"""
Give a {strength} hint for this pop culture trivia question.
Do NOT reveal the answer directly.

Question: {question}
Answer: {correct_answer}
Hint number: {hint_number} of 2
Hint must be under 20 words.
""".strip()}
        ]
        text = _generate(messages=messages, temperature=0.7, max_tokens=60, wiki_grounding=False)
        if text and len(text.strip()) > 5:
            return text.strip().strip('"')

    answer = correct_answer.strip()
    if hint_number == 1:
        return f"The answer starts with '{answer[0]}' and has {len(answer)} characters."
    revealed = answer[: max(1, len(answer)//2)]
    return f"The answer begins with '{revealed}...'"


def generate_explanation(question: str, correct_answer: str,
                         user_answer: str, is_correct: bool) -> dict:
    if is_ai_ready():
        status = "correctly" if is_correct else "incorrectly"
        messages = [
            {"role": "system", "content": "Return JSON only."},
            {"role": "user", "content": f"""
The user answered this pop culture trivia question {status}.

Question: {question}
Correct Answer: {correct_answer}
User Answer: {user_answer}

Return ONLY JSON:
{{
  "verdict": "1 sentence verdict",
  "explanation": "2-3 sentences educational explanation",
  "fun_fact": "one short fun fact"
}}
""".strip()}
        ]
        text = _generate(messages=messages, temperature=0.7, max_tokens=260, wiki_grounding=True)
        result = _parse_json_response(text or "")
        if result and "explanation" in result:
            return {
                "verdict": result.get("verdict", ""),
                "explanation": result.get("explanation", ""),
                "fun_fact": result.get("fun_fact", ""),
            }

    verdict = (f"✅ Correct! The answer is {correct_answer}."
               if is_correct else f"❌ Incorrect. The correct answer is {correct_answer}.")
    return {
        "verdict": verdict,
        "explanation": f"The answer to this question is {correct_answer}.",
        "fun_fact": "Pop culture is full of fun details—keep going!",
    }


def generate_daily_challenge() -> dict | None:
    if is_ai_ready():
        themes = [
            "Iconic Movies", "TV Legends", "Pop Anthems",
            "Award Show Moments", "Famous Characters",
            "90s Nostalgia", "Superheroes", "Anime Classics",
        ]
        theme = random.choice(themes)

        messages = [
            {"role": "system", "content": "You create daily pop culture trivia. Return JSON only."},
            {"role": "user", "content": f"""
Generate a themed pop culture daily challenge about "{theme}".
Create exactly {DAILY_CHALLENGE_QUESTIONS} multiple-choice questions with increasing difficulty (1 to 5).

Return ONLY JSON:
{{
  "theme": "{theme}",
  "questions": [
    {{
      "question": "text",
      "options": ["A","B","C","D"],
      "correct_answer": "one option exactly",
      "difficulty": 1,
      "topic": "TV or Movies or Music",
      "explanation": "brief explanation",
      "fun_fact": "fun fact"
    }}
  ]
}}
""".strip()}
        ]

        text = _generate(messages=messages, temperature=0.8, max_tokens=1200, wiki_grounding=True)
        result = _parse_json_response(text or "")
        if result and "questions" in result and len(result["questions"]) > 0:
            return result

    questions = _load_fallback()
    if questions and len(questions) >= DAILY_CHALLENGE_QUESTIONS:
        selected = random.sample(questions, DAILY_CHALLENGE_QUESTIONS)
        return {"theme": "Pop Culture Mix", "questions": selected}
    return None
