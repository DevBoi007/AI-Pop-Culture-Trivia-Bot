"""
AI Culture Trivia Chatbot — Main Entry Point
Streamlit application that orchestrates quiz flow, AI integration, and user experience.
"""

import time
import streamlit as st
from datetime import date

from config import (
    GAME_MODES, TOPICS, CHALLENGE_TIME_LIMIT,
    MAX_HINTS_PER_QUESTION, DIFFICULTY_LABELS, DAILY_CHALLENGE_QUESTIONS,
)
from database import (
    init_db, get_or_create_user, create_session, update_session,
    save_answer, get_user_stats, get_leaderboard, get_daily_leaderboard,
    save_daily_challenge, get_daily_challenge, save_daily_score,
    has_completed_daily,
)
from ai_engine import (
    init_gemini, test_gemini_connection, is_ai_ready,
    generate_question, evaluate_answer,
    generate_hint, generate_explanation, generate_daily_challenge,
)
from quiz_logic import QuizSession
from ui import (
    inject_custom_css, render_hero, render_mode_selector,
    render_question_card, render_timer, render_feedback,
    render_hint, render_score_header, render_session_summary,
    render_leaderboard, render_stats_charts, render_sidebar_user_info,
)


# ─── Page Config ──────────────────────────────────────────

st.set_page_config(
    page_title="Pop Culture Trivia Bot",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Initialize ──────────────────────────────────────────

inject_custom_css()
init_db()


# ─── Session State Defaults ──────────────────────────────

DEFAULTS = {
    "page": "home",
    "username": "",
    "user": None,
    "logged_in": False,
    "selected_mode": None,
    "quiz_session": None,
    "session_id": None,
    "current_question": None,
    "feedback": None,
    "explanation": None,
    "hints": [],
    "answered": False,
    "user_answer": None,
    "question_start": None,
    "selected_topics": list(TOPICS),
    "api_key": "",
    "ai_initialized": False,
    "daily_challenge": None,
    "daily_question_idx": 0,
    "daily_score": 0,
    "daily_correct": 0,
    "daily_answered": False,
    "daily_feedback": None,
    "daily_explanation": None,
}

for key, val in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = val

# ─── Auto-reinit AI on page reload ──────────────────────
# Streamlit reruns the whole script on every interaction.
# _api_ready is a module-level variable that resets to False.
# If the user already entered a key this session, reinitialize silently.
if st.session_state.api_key and not is_ai_ready():
    init_gemini(st.session_state.api_key)



# ─── Sidebar ─────────────────────────────────────────────

def render_sidebar():
    """Render the sidebar with login, settings, and navigation."""
    with st.sidebar:
        st.markdown("""
            <div style="text-align: center; margin-bottom: 20px;">
                <span style="font-size: 2rem;">🎬</span>
                <span style="font-size: 1.3rem; font-weight: 700; margin-left: 8px;">Pop Culture Trivia</span>
            </div>
        """, unsafe_allow_html=True)

        # ── User Login ──
        if not st.session_state.logged_in:
            st.markdown("#### 👤 Enter Your Name")
            username = st.text_input("Username", placeholder="e.g. Explorer42",
                                     label_visibility="collapsed", key="username_input")
            if st.button("🚀 Start Playing", use_container_width=True):
                if username.strip():
                    user = get_or_create_user(username.strip())
                    st.session_state.username = username.strip()
                    st.session_state.user = user
                    st.session_state.logged_in = True
                    st.rerun()
                else:
                    st.warning("Please enter a name!")
        else:
            # Show user stats
            stats = get_user_stats(st.session_state.user["id"])
            render_sidebar_user_info(st.session_state.username, stats)

            st.markdown("---")

            # ── Navigation ──
            st.markdown("#### 🧭 Navigation")
            nav_items = {
                "home": "🏠 Home",
                "leaderboard": "🏆 Leaderboard",
                "stats": "📊 My Stats",
                "daily": "📅 Daily Challenge",
            }
            for key, label in nav_items.items():
                if st.button(label, key=f"nav_{key}", use_container_width=True):
                    # Reset quiz state when navigating away
                    if key != "quiz":
                        st.session_state.quiz_session = None
                        st.session_state.current_question = None
                        st.session_state.answered = False
                        st.session_state.feedback = None
                        st.session_state.hints = []
                    st.session_state.page = key
                    st.rerun()

            st.markdown("---")

            # ── Topic Selection ──
            st.markdown("#### 🎯 Preferred Topics")
            selected = []
            for topic in TOPICS:
                if st.checkbox(topic, value=topic in st.session_state.selected_topics,
                               key=f"topic_{topic}"):
                    selected.append(topic)
            st.session_state.selected_topics = selected if selected else list(TOPICS)

            st.markdown("---")

            # ── AI Configuration ──
            st.markdown("#### 🤖 AI Settings")
            api_key = st.text_input(
                "Sarvam API Key", type="password",
                value=st.session_state.api_key,
                placeholder="Paste your API subscription key here",
                key="api_key_input",
            )

            if api_key and api_key != st.session_state.api_key:
                # New key entered — initialize
                st.session_state.api_key = api_key
                success, err_msg = init_gemini(api_key)
                st.session_state.ai_initialized = success
                if success:
                    # Now do a live connection test
                    with st.spinner("🔌 Verifying connection..."):
                        ok, test_err = test_gemini_connection()
                    if ok:
                        st.success("✅ AI Connected & Verified!")
                    else:
                        st.warning(f"⚠️ Key accepted but test call failed: {test_err}")
                else:
                    st.error(f"❌ {err_msg}")

            if is_ai_ready():
                st.markdown("""
                    <div style="display:flex;align-items:center;gap:8px;margin-top:4px;">
                        <div style="width:8px;height:8px;border-radius:50%;background:#00E676;"></div>
                        <span style="color:#00E676;font-size:0.85rem;">AI Active — Dynamic questions enabled</span>
                    </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown("""
                    <div style="display:flex;align-items:center;gap:8px;margin-top:4px;">
                        <div style="width:8px;height:8px;border-radius:50%;background:#FF9800;"></div>
                        <span style="color:#FF9800;font-size:0.85rem;">Offline Mode</span>
                    </div>
                """, unsafe_allow_html=True)


            st.markdown("---")
            if st.button("🚪 Log Out", use_container_width=True):
                for key in DEFAULTS:
                    st.session_state[key] = DEFAULTS[key]
                st.rerun()


# ─── Pages ────────────────────────────────────────────────

def page_home():
    """Home page with mode selection."""
    render_hero()
    render_mode_selector()

    # Quick stats
    if st.session_state.logged_in:
        st.markdown("---")
        stats = get_user_stats(st.session_state.user["id"])
        if stats.get("total_sessions", 0) > 0:
            cols = st.columns(4)
            items = [
                ("🎮", str(stats.get("total_sessions", 0)), "Games Played"),
                ("⭐", str(stats.get("total_score", 0)), "Total Score"),
                ("🎯", f"{round(stats.get('avg_accuracy', 0), 1)}%", "Avg Accuracy"),
                ("📈", DIFFICULTY_LABELS.get(
                    stats.get("max_difficulty", 1), ("Beginner", "🟢")
                )[1] + " " + DIFFICULTY_LABELS.get(
                    stats.get("max_difficulty", 1), ("Beginner", "🟢")
                )[0], "Peak Level"),
            ]
            for col, (icon, value, label) in zip(cols, items):
                with col:
                    st.markdown(f"""
                        <div class="stat-box">
                            <div style="font-size: 1.6rem; margin-bottom: 4px;">{icon}</div>
                            <div class="stat-value" style="font-size: 1.5rem;">{value}</div>
                            <div class="stat-label">{label}</div>
                        </div>
                    """, unsafe_allow_html=True)


def page_quiz():
    """Main quiz page — handles all game modes."""
    if not st.session_state.logged_in:
        st.warning("Please log in to play!")
        return

    mode = st.session_state.selected_mode or "quiz"
    mode_info = GAME_MODES.get(mode, GAME_MODES["quiz"])

    # ── Initialize session ──
    if st.session_state.quiz_session is None:
        quiz = QuizSession(mode=mode, user_id=st.session_state.user["id"])
        st.session_state.quiz_session = quiz
        st.session_state.session_id = create_session(
            st.session_state.user["id"], mode
        )
        st.session_state.current_question = None
        st.session_state.answered = False
        st.session_state.feedback = None
        st.session_state.explanation = None
        st.session_state.hints = []

    quiz: QuizSession = st.session_state.quiz_session

    # ── Check if finished ──
    if quiz.is_finished:
        _render_quiz_complete(quiz)
        return

    # ── Score Header ──
    render_score_header(quiz.score, quiz.current_streak, quiz.accuracy)

    # ── Generate question if needed ──
    if st.session_state.current_question is None:
        with st.spinner("🤔 Generating question..."):
            topic = quiz.get_next_topic()
            # Filter to selected topics
            if st.session_state.selected_topics:
                topics_pool = st.session_state.selected_topics
                topic = topic if topic in topics_pool else topics_pool[0]

            question = generate_question(
                topic=topic,
                difficulty=quiz.difficulty.get_difficulty(),
                asked_questions=quiz.asked_questions,
            )
            if question:
                quiz.set_current_question(question)
                st.session_state.current_question = question
                st.session_state.question_start = time.time()
                st.session_state.answered = False
                st.session_state.feedback = None
                st.session_state.explanation = None
                st.session_state.hints = []
            else:
                st.error("Could not generate a question. Please try again.")
                return

    question = st.session_state.current_question
    total_q = quiz.total_questions if quiz.total_questions > 0 else "∞"

    # ── Render Question ──
    render_question_card(
        question,
        question_num=quiz.questions_answered + 1,
        total=quiz.total_questions if quiz.total_questions > 0 else 0,
    )

    # ── Timer (Challenge Mode) ──
    if quiz.is_timed and not st.session_state.answered:
        elapsed = time.time() - (st.session_state.question_start or time.time())
        remaining = max(0, CHALLENGE_TIME_LIMIT - elapsed)
        render_timer(remaining)

        if remaining <= 0:
            # Time's up!
            st.session_state.answered = True
            st.session_state.user_answer = ""
            _process_answer(quiz, question, "", time_taken=CHALLENGE_TIME_LIMIT)
            st.rerun()

    # ── Answer Area ──
    if not st.session_state.answered:
        options = question.get("options", [])
        if options:
            answer = st.radio(
                "Select your answer:",
                options,
                key=f"answer_{quiz.questions_answered}",
                index=None,
                label_visibility="collapsed",
            )
        else:
            answer = st.text_input(
                "Type your answer:",
                key=f"text_answer_{quiz.questions_answered}",
                placeholder="Type your answer here...",
            )

        # ── Action Buttons ──
        btn_cols = st.columns([2, 1, 1])
        with btn_cols[0]:
            if st.button("✅ Submit Answer", use_container_width=True, type="primary"):
                if answer:
                    elapsed = time.time() - (st.session_state.question_start or time.time())
                    st.session_state.user_answer = answer
                    st.session_state.answered = True
                    _process_answer(quiz, question, answer, time_taken=elapsed)
                    st.rerun()
                else:
                    st.warning("Please select or type an answer!")

        with btn_cols[1]:
            hints_used = len(st.session_state.hints)
            hint_label = f"💡 Hint ({MAX_HINTS_PER_QUESTION - hints_used} left)"
            if st.button(hint_label, use_container_width=True,
                         disabled=hints_used >= MAX_HINTS_PER_QUESTION):
                hint_num = hints_used + 1
                hint = generate_hint(
                    question.get("question", ""),
                    question.get("correct_answer", ""),
                    hint_number=hint_num,
                )
                st.session_state.hints.append(hint)
                quiz.use_hint()
                st.rerun()

        with btn_cols[2]:
            if mode == "learning":
                if st.button("⏭ Skip", use_container_width=True):
                    st.session_state.answered = True
                    _process_answer(quiz, question, "", time_taken=0)
                    st.rerun()

        # ── Show active hints ──
        for i, h in enumerate(st.session_state.hints):
            render_hint(h, i + 1)

    else:
        # ── Show Feedback ──
        if st.session_state.feedback is not None:
            render_feedback(
                st.session_state.feedback["is_correct"],
                st.session_state.explanation or {}
            )

            # Points awarded
            points = st.session_state.feedback.get("points", 0)
            if points > 0:
                st.markdown(f"""
                    <div style="text-align: center; margin: 12px 0;">
                        <span class="streak-badge">+{points} points!</span>
                    </div>
                """, unsafe_allow_html=True)

        # ── Next Question Button ──
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if quiz.total_questions > 0 and quiz.questions_answered >= quiz.total_questions:
                if st.button("🏆 See Results", use_container_width=True, type="primary"):
                    _finalize_session(quiz)
                    st.rerun()
            else:
                next_label = "➡️ Next Question"
                if mode == "learning":
                    next_label = "➡️ Next Question"
                if st.button(next_label, use_container_width=True, type="primary"):
                    st.session_state.current_question = None
                    st.session_state.answered = False
                    st.rerun()

                if mode == "learning":
                    if st.button("🏁 End Session", use_container_width=True):
                        _finalize_session(quiz)
                        st.rerun()


def _process_answer(quiz: QuizSession, question: dict, user_answer: str,
                    time_taken: float = 0):
    """Process a submitted answer."""
    correct_answer = question.get("correct_answer", "")

    # Evaluate
    eval_result = evaluate_answer(
        question.get("question", ""),
        user_answer,
        correct_answer,
        question.get("options", []),
    )
    is_correct = eval_result.get("is_correct", False)

    # Score
    points = quiz.record_answer(is_correct, time_taken)

    # Generate explanation
    explanation = None
    if question.get("explanation"):
        # Use pre-built explanation from dataset
        explanation = {
            "verdict": f"{'✅ Correct!' if is_correct else '❌ Incorrect.'} The answer is {correct_answer}.",
            "explanation": question.get("explanation", ""),
            "fun_fact": question.get("fun_fact", ""),
        }
    else:
        explanation = generate_explanation(
            question.get("question", ""),
            correct_answer,
            user_answer,
            is_correct,
        )

    st.session_state.feedback = {
        "is_correct": is_correct,
        "points": points,
        "eval": eval_result,
    }
    st.session_state.explanation = explanation

    # Save to database
    save_answer(
        session_id=st.session_state.session_id,
        question_text=question.get("question", ""),
        user_answer=user_answer,
        correct_answer=correct_answer,
        is_correct=is_correct,
        score_awarded=points,
        difficulty=question.get("difficulty", 2),
        topic=question.get("topic", "General"),
        time_taken=time_taken,
        hints_used=len(st.session_state.hints),
    )


def _finalize_session(quiz: QuizSession):
    """Finalize and save the quiz session."""
    summary = quiz.get_summary()
    update_session(
        session_id=st.session_state.session_id,
        score=summary["score"],
        total_questions=summary["questions_answered"],
        correct_answers=summary["correct_answers"],
        difficulty_reached=summary["difficulty_reached"],
    )
    st.session_state.page = "results"


def _render_quiz_complete(quiz: QuizSession):
    """Render when all questions are answered."""
    _finalize_session(quiz)
    summary = quiz.get_summary()
    render_session_summary(summary)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🏠 Back to Home", use_container_width=True, type="primary"):
            st.session_state.quiz_session = None
            st.session_state.current_question = None
            st.session_state.page = "home"
            st.rerun()
        if st.button("🔄 Play Again", use_container_width=True):
            st.session_state.quiz_session = None
            st.session_state.current_question = None
            st.session_state.page = "quiz"
            st.rerun()


def page_results():
    """Results page after a quiz session."""
    if st.session_state.quiz_session is None:
        st.session_state.page = "home"
        st.rerun()
        return

    quiz: QuizSession = st.session_state.quiz_session
    summary = quiz.get_summary()
    render_session_summary(summary)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🏠 Back to Home", use_container_width=True, type="primary"):
            st.session_state.quiz_session = None
            st.session_state.current_question = None
            st.session_state.page = "home"
            st.rerun()
        if st.button("🔄 Play Again", use_container_width=True):
            st.session_state.quiz_session = None
            st.session_state.current_question = None
            st.session_state.page = "quiz"
            st.rerun()


def page_leaderboard():
    """Leaderboard page."""
    st.markdown("""
        <div class="hero-title" style="font-size: 2.2rem;">🏆 Leaderboard</div>
    """, unsafe_allow_html=True)

    tab1, tab2, tab3, tab4 = st.tabs(["🌐 All Modes", "🎯 Quiz", "⚡ Challenge", "📅 Daily"])

    with tab1:
        entries = get_leaderboard(limit=15)
        render_leaderboard(entries, "Top Scores — All Modes")

    with tab2:
        entries = get_leaderboard(mode="quiz", limit=15)
        render_leaderboard(entries, "Top Scores — Quiz Mode")

    with tab3:
        entries = get_leaderboard(mode="challenge", limit=15)
        render_leaderboard(entries, "Top Scores — Challenge Mode")

    with tab4:
        entries = get_daily_leaderboard()
        render_leaderboard(entries, f"Daily Challenge — {date.today().strftime('%B %d, %Y')}")


def page_stats():
    """User statistics page."""
    if not st.session_state.logged_in:
        st.warning("Please log in to see your stats!")
        return

    st.markdown("""
        <div class="hero-title" style="font-size: 2.2rem;">📊 Your Stats</div>
    """, unsafe_allow_html=True)

    stats = get_user_stats(st.session_state.user["id"])

    if stats.get("total_sessions", 0) == 0:
        st.markdown(f"""
            <div class="trivia-card" style="text-align: center;">
                <div style="font-size: 3rem; margin-bottom: 12px;">🎮</div>
                <div style="font-size: 1.2rem; font-weight: 600;">No games yet!</div>
                <div style="color: {THEME['text_secondary']}; margin-top: 8px;">
                    Play your first quiz to see your stats here.
                </div>
            </div>
        """, unsafe_allow_html=True)
        return

    # Overview
    cols = st.columns(4)
    items = [
        ("🎮", str(stats["total_sessions"]), "Games"),
        ("⭐", str(stats["total_score"]), "Total Score"),
        ("✅", str(stats.get("total_correct", 0)), "Correct Answers"),
        ("🎯", f"{round(stats['avg_accuracy'], 1)}%", "Avg Accuracy"),
    ]
    for col, (icon, val, label) in zip(cols, items):
        with col:
            st.markdown(f"""
                <div class="stat-box">
                    <div style="font-size: 1.4rem;">{icon}</div>
                    <div class="stat-value" style="font-size: 1.5rem;">{val}</div>
                    <div class="stat-label">{label}</div>
                </div>
            """, unsafe_allow_html=True)

    render_stats_charts(stats)


def page_daily():
    """Daily Challenge page."""
    if not st.session_state.logged_in:
        st.warning("Please log in to play the Daily Challenge!")
        return

    st.markdown(f"""
        <div style="text-align: center; padding: 20px 0;">
            <div style="font-size: 3rem;">📅</div>
            <div class="hero-title" style="font-size: 2rem;">Daily Challenge</div>
            <div style="color: {THEME['text_secondary']};">
                {date.today().strftime('%A, %B %d, %Y')}
            </div>
        </div>
    """, unsafe_allow_html=True)

    user_id = st.session_state.user["id"]
    today = date.today().isoformat()

    # Check if already completed
    if has_completed_daily(user_id, today):
        st.markdown(f"""
            <div class="trivia-card" style="text-align: center;">
                <div style="font-size: 2.5rem; margin-bottom: 10px;">✅</div>
                <div style="font-size: 1.2rem; font-weight: 600;">You've completed today's challenge!</div>
                <div style="color: {THEME['text_secondary']}; margin-top: 8px;">
                    Come back tomorrow for a new challenge.
                </div>
            </div>
        """, unsafe_allow_html=True)

        # Show daily leaderboard
        entries = get_daily_leaderboard(today)
        render_leaderboard(entries, "Today's Rankings")
        return

    # Load or generate daily challenge
    if st.session_state.daily_challenge is None:
        challenge = get_daily_challenge(today)
        if challenge is None:
            with st.spinner("🎲 Generating today's challenge..."):
                challenge_data = generate_daily_challenge()
                if challenge_data:
                    save_daily_challenge(today, challenge_data.get("theme", "Mixed"),
                                         challenge_data["questions"])
                    challenge = {
                        "theme": challenge_data.get("theme", "Mixed"),
                        "questions": challenge_data["questions"],
                    }
                else:
                    st.error("Could not generate daily challenge. Try again later.")
                    return
        else:
            challenge = {
                "theme": challenge.get("theme", "Mixed"),
                "questions": challenge.get("questions", []),
            }

        st.session_state.daily_challenge = challenge
        st.session_state.daily_question_idx = 0
        st.session_state.daily_score = 0
        st.session_state.daily_correct = 0
        st.session_state.daily_answered = False
        st.session_state.daily_feedback = None
        st.session_state.daily_explanation = None

    challenge = st.session_state.daily_challenge
    questions = challenge.get("questions", [])
    idx = st.session_state.daily_question_idx

    st.markdown(f"""
        <div style="text-align: center; margin-bottom: 16px;">
            <span class="topic-chip" style="font-size: 0.9rem; padding: 6px 16px;">
                🎯 Theme: {challenge.get('theme', 'World Culture Mix')}
            </span>
        </div>
    """, unsafe_allow_html=True)

    if idx >= len(questions):
        # Daily challenge complete
        save_daily_score(user_id, today, st.session_state.daily_score,
                         st.session_state.daily_correct)

        st.markdown(f"""
            <div style="text-align: center; padding: 30px 0;">
                <div style="font-size: 3rem;">🎉</div>
                <div class="hero-title" style="font-size: 2rem;">Challenge Complete!</div>
                <div class="score-display">{st.session_state.daily_score} pts</div>
                <div style="color: {THEME['text_secondary']}; margin-top: 8px;">
                    {st.session_state.daily_correct}/{len(questions)} correct answers
                </div>
            </div>
        """, unsafe_allow_html=True)

        entries = get_daily_leaderboard(today)
        render_leaderboard(entries, "Today's Rankings")

        if st.button("🏠 Back to Home", use_container_width=True):
            st.session_state.daily_challenge = None
            st.session_state.page = "home"
            st.rerun()
        return

    # Show current question
    question = questions[idx]

    # Score display
    cols = st.columns(3)
    with cols[0]:
        st.markdown(f"""
            <div class="stat-box">
                <div class="stat-value">{st.session_state.daily_score}</div>
                <div class="stat-label">Score</div>
            </div>
        """, unsafe_allow_html=True)
    with cols[1]:
        st.markdown(f"""
            <div class="stat-box">
                <div class="stat-value" style="color: {THEME['accent']};">{idx + 1}/{len(questions)}</div>
                <div class="stat-label">Question</div>
            </div>
        """, unsafe_allow_html=True)
    with cols[2]:
        st.markdown(f"""
            <div class="stat-box">
                <div class="stat-value" style="color: {THEME['success']};">{st.session_state.daily_correct}</div>
                <div class="stat-label">Correct</div>
            </div>
        """, unsafe_allow_html=True)

    render_question_card(question, idx + 1, len(questions))

    if not st.session_state.daily_answered:
        options = question.get("options", [])
        if options:
            answer = st.radio("Select:", options, key=f"daily_{idx}",
                              index=None, label_visibility="collapsed")
        else:
            answer = st.text_input("Answer:", key=f"daily_text_{idx}")

        if st.button("✅ Submit", use_container_width=True, type="primary"):
            if answer:
                correct = question.get("correct_answer", "")
                eval_result = evaluate_answer(question.get("question", ""),
                                               answer, correct, options)
                is_correct = eval_result["is_correct"]

                diff = question.get("difficulty", 2)
                points = int(BASE_POINTS * (1 + (diff - 1) * 0.5)) if is_correct else 0
                st.session_state.daily_score += points
                if is_correct:
                    st.session_state.daily_correct += 1

                st.session_state.daily_answered = True
                st.session_state.daily_feedback = {
                    "is_correct": is_correct, "points": points
                }
                st.session_state.daily_explanation = {
                    "verdict": f"{'✅ Correct!' if is_correct else '❌ Incorrect.'} The answer is {correct}.",
                    "explanation": question.get("explanation", ""),
                    "fun_fact": question.get("fun_fact", ""),
                }
                st.rerun()
            else:
                st.warning("Please select an answer!")
    else:
        fb = st.session_state.daily_feedback
        render_feedback(fb["is_correct"], st.session_state.daily_explanation or {})

        if fb.get("points", 0) > 0:
            st.markdown(f"""
                <div style="text-align: center; margin: 12px 0;">
                    <span class="streak-badge">+{fb['points']} points!</span>
                </div>
            """, unsafe_allow_html=True)

        if st.button("➡️ Next Question", use_container_width=True, type="primary"):
            st.session_state.daily_question_idx += 1
            st.session_state.daily_answered = False
            st.session_state.daily_feedback = None
            st.session_state.daily_explanation = None
            st.rerun()


# ─── Import config THEME in this scope ──
from config import THEME, BASE_POINTS


# ─── Router ──────────────────────────────────────────────

def main():
    """Main router."""
    render_sidebar()

    if not st.session_state.logged_in:
        render_hero()
        st.markdown(f"""
            <div class="trivia-card" style="text-align: center;">
                <div style="font-size: 2rem; margin-bottom: 10px;">👈</div>
                <div style="font-size: 1.1rem; font-weight: 600;">Enter your name in the sidebar to get started!</div>
                <div style="color: {THEME['text_secondary']}; margin-top: 8px;">
                    Challenge yourself with AI-powered trivia from TV, movies, and music.
                </div>
            </div>
        """, unsafe_allow_html=True)
        return

    page = st.session_state.page
    if page == "home":
        page_home()
    elif page == "quiz":
        page_quiz()
    elif page == "results":
        page_results()
    elif page == "leaderboard":
        page_leaderboard()
    elif page == "stats":
        page_stats()
    elif page == "daily":
        page_daily()
    else:
        page_home()


if __name__ == "__main__":
    main()
