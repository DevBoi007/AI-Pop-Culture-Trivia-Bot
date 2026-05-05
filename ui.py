"""
Streamlit UI components and styling for the AI Culture Trivia Chatbot.
Premium dark theme with gradient accents, animations, and polished layouts.
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from config import THEME, DIFFICULTY_LABELS, GAME_MODES, TOPICS, CHALLENGE_TIME_LIMIT


# ─── Custom CSS ───────────────────────────────────────────

def inject_custom_css():
    """Inject premium custom CSS into the Streamlit app."""
    st.markdown(f"""
    <style>
        /* ── Import Font ── */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

        /* ── Global ── */
        .stApp {{
            font-family: 'Inter', sans-serif;
        }}

        /* ── Hide streamlit branding ── */
        #MainMenu {{visibility: hidden;}}
        footer {{visibility: hidden;}}
        header {{visibility: hidden;}}

        /* ── Sidebar ── */
        section[data-testid="stSidebar"] {{
            background: linear-gradient(180deg, #13131a 0%, #1a1d29 100%);
            border-right: 1px solid rgba(108, 99, 255, 0.2);
        }}

        /* ── Cards ── */
        .trivia-card {{
            background: {THEME['bg_card']};
            border: 1px solid rgba(108, 99, 255, 0.15);
            border-radius: 16px;
            padding: 28px;
            margin: 14px 0;
            transition: all 0.3s ease;
            box-shadow: 0 4px 24px rgba(0,0,0,0.2);
        }}
        .trivia-card:hover {{
            border-color: rgba(108, 99, 255, 0.4);
            box-shadow: 0 8px 32px rgba(108, 99, 255, 0.1);
            transform: translateY(-2px);
        }}

        /* ── Question Card ── */
        .question-card {{
            background: linear-gradient(135deg, #1a1d29 0%, #252836 100%);
            border: 1px solid rgba(108, 99, 255, 0.25);
            border-radius: 20px;
            padding: 36px;
            margin: 20px 0;
            box-shadow: 0 8px 40px rgba(108, 99, 255, 0.08);
        }}
        .question-text {{
            font-size: 1.35rem;
            font-weight: 600;
            color: #fff;
            line-height: 1.6;
            margin-bottom: 12px;
        }}

        /* ── Difficulty Badges ── */
        .diff-badge {{
            display: inline-block;
            padding: 4px 14px;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 600;
            margin-bottom: 16px;
        }}
        .diff-1 {{ background: rgba(0, 230, 118, 0.15); color: #00E676; border: 1px solid rgba(0, 230, 118, 0.3); }}
        .diff-2 {{ background: rgba(0, 210, 255, 0.15); color: #00D2FF; border: 1px solid rgba(0, 210, 255, 0.3); }}
        .diff-3 {{ background: rgba(255, 214, 0, 0.15); color: #FFD600; border: 1px solid rgba(255, 214, 0, 0.3); }}
        .diff-4 {{ background: rgba(255, 152, 0, 0.15); color: #FF9800; border: 1px solid rgba(255, 152, 0, 0.3); }}
        .diff-5 {{ background: rgba(255, 82, 82, 0.15); color: #FF5252; border: 1px solid rgba(255, 82, 82, 0.3); }}

        /* ── Topic Chip ── */
        .topic-chip {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 0.75rem;
            font-weight: 500;
            background: rgba(108, 99, 255, 0.12);
            color: {THEME['primary']};
            border: 1px solid rgba(108, 99, 255, 0.25);
            margin-left: 8px;
        }}

        /* ── Score Display ── */
        .score-display {{
            background: linear-gradient(135deg, {THEME['primary']} 0%, #00D2FF 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-size: 2.8rem;
            font-weight: 800;
            text-align: center;
        }}

        /* ── Stat Box ── */
        .stat-box {{
            background: {THEME['bg_card']};
            border: 1px solid rgba(255,255,255,0.06);
            border-radius: 14px;
            padding: 20px;
            text-align: center;
        }}
        .stat-value {{
            font-size: 1.8rem;
            font-weight: 700;
            color: {THEME['primary']};
        }}
        .stat-label {{
            font-size: 0.85rem;
            color: {THEME['text_secondary']};
            margin-top: 4px;
        }}

        /* ── Correct / Incorrect Feedback ── */
        .feedback-correct {{
            background: linear-gradient(135deg, rgba(0,230,118,0.08) 0%, rgba(0,210,255,0.05) 100%);
            border: 1px solid rgba(0,230,118,0.3);
            border-radius: 16px;
            padding: 24px;
            margin: 16px 0;
        }}
        .feedback-incorrect {{
            background: linear-gradient(135deg, rgba(255,82,82,0.08) 0%, rgba(255,152,0,0.05) 100%);
            border: 1px solid rgba(255,82,82,0.3);
            border-radius: 16px;
            padding: 24px;
            margin: 16px 0;
        }}

        /* ── Fun Fact Box ── */
        .fun-fact {{
            background: rgba(255, 214, 0, 0.06);
            border-left: 3px solid {THEME['warning']};
            padding: 14px 18px;
            border-radius: 0 10px 10px 0;
            margin: 10px 0;
            font-size: 0.92rem;
            color: #FFD600;
        }}

        /* ── Mode Card ── */
        .mode-card {{
            background: {THEME['bg_card']};
            border: 1px solid rgba(255,255,255,0.06);
            border-radius: 16px;
            padding: 24px;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s ease;
        }}
        .mode-card:hover {{
            border-color: {THEME['primary']};
            transform: translateY(-4px);
            box-shadow: 0 12px 40px rgba(108,99,255,0.15);
        }}

        /* ── Timer Bar ── */
        .timer-bar-container {{
            background: rgba(255,255,255,0.06);
            border-radius: 8px;
            height: 8px;
            margin: 12px 0;
            overflow: hidden;
        }}
        .timer-bar {{
            height: 100%;
            border-radius: 8px;
            transition: width 1s linear;
        }}

        /* ── Leaderboard ── */
        .lb-row {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 12px 16px;
            border-radius: 10px;
            margin: 6px 0;
            background: {THEME['bg_card']};
            border: 1px solid rgba(255,255,255,0.04);
        }}
        .lb-rank {{
            font-weight: 700;
            width: 36px;
            text-align: center;
        }}
        .lb-gold {{ color: #FFD700; }}
        .lb-silver {{ color: #C0C0C0; }}
        .lb-bronze {{ color: #CD7F32; }}

        /* ── Progress Bar ── */
        .progress-container {{
            background: rgba(255,255,255,0.06);
            border-radius: 10px;
            height: 10px;
            margin: 8px 0;
        }}
        .progress-fill {{
            height: 100%;
            border-radius: 10px;
            background: {THEME['gradient_1']};
            transition: width 0.5s ease;
        }}

        /* ── Hero Title ── */
        .hero-title {{
            font-size: 3rem;
            font-weight: 800;
            background: linear-gradient(135deg, {THEME['primary']} 0%, #00D2FF 50%, {THEME['secondary']} 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            text-align: center;
            margin-bottom: 8px;
            line-height: 1.2;
        }}
        .hero-subtitle {{
            text-align: center;
            color: {THEME['text_secondary']};
            font-size: 1.1rem;
            margin-bottom: 36px;
        }}

        /* ── Button styling ── */
        .stButton > button {{
            border-radius: 12px;
            font-weight: 600;
            font-family: 'Inter', sans-serif;
            transition: all 0.3s ease;
            border: 1px solid rgba(108,99,255,0.3);
        }}
        .stButton > button:hover {{
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(108,99,255,0.25);
        }}

        /* ── Hint text ── */
        .hint-text {{
            background: rgba(0, 210, 255, 0.08);
            border: 1px solid rgba(0, 210, 255, 0.2);
            border-radius: 12px;
            padding: 14px 18px;
            margin: 10px 0;
            color: #00D2FF;
            font-size: 0.92rem;
        }}

        /* ── Streak badge ── */
        .streak-badge {{
            display: inline-block;
            padding: 6px 16px;
            border-radius: 20px;
            font-size: 0.85rem;
            font-weight: 600;
            background: linear-gradient(135deg, #FF6584 0%, #FFD600 100%);
            color: #000;
        }}

        /* ── Answer Options ── */
        div[data-testid="stRadio"] label {{
            background: {THEME['bg_card']};
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 12px;
            padding: 12px 18px !important;
            margin: 6px 0 !important;
            transition: all 0.2s ease;
        }}
        div[data-testid="stRadio"] label:hover {{
            border-color: {THEME['primary']};
            background: rgba(108,99,255,0.08);
        }}
    </style>
    """, unsafe_allow_html=True)


# ─── UI Components ────────────────────────────────────────

def render_hero():
    """Render the hero/landing section."""
    st.markdown("""
        <div style="text-align: center; padding: 40px 0 20px;">
            <div style="font-size: 4rem; margin-bottom: 10px;">🌍</div>
            <div class="hero-title">Culture Trivia</div>
            <div class="hero-subtitle">
                Explore world cultures through AI-powered trivia — history, festivals, food, geography & languages
            </div>
        </div>
    """, unsafe_allow_html=True)


def render_mode_selector():
    """Render game mode selection cards."""
    st.markdown("### Choose Your Mode")
    cols = st.columns(3)

    for i, (mode_key, mode_info) in enumerate(GAME_MODES.items()):
        with cols[i]:
            st.markdown(f"""
                <div class="mode-card">
                    <div style="font-size: 2.2rem; margin-bottom: 12px;">{mode_info['name'].split(' ')[0]}</div>
                    <div style="font-weight: 600; font-size: 1.05rem; margin-bottom: 8px;">
                        {mode_info['name'].split(' ', 1)[1] if ' ' in mode_info['name'] else mode_info['name']}
                    </div>
                    <div style="color: {THEME['text_secondary']}; font-size: 0.85rem;">
                        {mode_info['description']}
                    </div>
                </div>
            """, unsafe_allow_html=True)
            if st.button(f"Play {mode_info['name'].split(' ', 1)[1]}", key=f"mode_{mode_key}",
                         use_container_width=True):
                st.session_state.selected_mode = mode_key
                st.session_state.page = "quiz"
                st.rerun()


def render_question_card(question: dict, question_num: int = 1, total: int = 10):
    """Render the question card with difficulty badge and topic chip."""
    diff = question.get("difficulty", 2)
    diff_label, diff_emoji = DIFFICULTY_LABELS.get(diff, ("Medium", "🟡"))
    topic = question.get("topic", "General")

    # Progress bar
    if total > 0:
        progress = question_num / total
        st.markdown(f"""
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                <span style="color: {THEME['text_secondary']}; font-size: 0.85rem;">
                    Question {question_num} of {total}
                </span>
                <span style="color: {THEME['text_secondary']}; font-size: 0.85rem;">
                    {int(progress * 100)}%
                </span>
            </div>
            <div class="progress-container">
                <div class="progress-fill" style="width: {progress * 100}%;"></div>
            </div>
        """, unsafe_allow_html=True)

    st.markdown(f"""
        <div class="question-card">
            <div>
                <span class="diff-badge diff-{diff}">{diff_emoji} {diff_label}</span>
                <span class="topic-chip">📌 {topic}</span>
            </div>
            <div class="question-text">{question.get('question', '')}</div>
        </div>
    """, unsafe_allow_html=True)


def render_timer(time_remaining: float, total_time: float = CHALLENGE_TIME_LIMIT):
    """Render a countdown timer bar."""
    pct = max(0, min(100, (time_remaining / total_time) * 100))
    if pct > 50:
        color = THEME['success']
    elif pct > 25:
        color = THEME['warning']
    else:
        color = THEME['error']

    st.markdown(f"""
        <div style="display: flex; align-items: center; gap: 12px; margin: 8px 0;">
            <span style="font-size: 1.4rem;">⏱️</span>
            <div class="timer-bar-container" style="flex: 1;">
                <div class="timer-bar" style="width: {pct}%; background: {color};"></div>
            </div>
            <span style="font-weight: 700; color: {color}; font-size: 1.1rem; min-width: 40px;">
                {int(time_remaining)}s
            </span>
        </div>
    """, unsafe_allow_html=True)


def render_feedback(is_correct: bool, explanation: dict):
    """Render answer feedback with explanation and fun fact."""
    css_class = "feedback-correct" if is_correct else "feedback-incorrect"
    icon = "🎉" if is_correct else "😔"

    verdict = explanation.get("verdict", "")
    explain_text = explanation.get("explanation", "")
    fun_fact = explanation.get("fun_fact", "")

    st.markdown(f"""
        <div class="{css_class}">
            <div style="font-size: 1.4rem; margin-bottom: 10px;">{icon} {verdict}</div>
            <div style="color: {THEME['text_secondary']}; font-size: 0.95rem; line-height: 1.6;">
                {explain_text}
            </div>
        </div>
    """, unsafe_allow_html=True)

    if fun_fact:
        st.markdown(f"""
            <div class="fun-fact">💡 <strong>Fun Fact:</strong> {fun_fact}</div>
        """, unsafe_allow_html=True)


def render_hint(hint_text: str, hint_number: int):
    """Render a hint."""
    st.markdown(f"""
        <div class="hint-text">
            🔍 <strong>Hint {hint_number}:</strong> {hint_text}
        </div>
    """, unsafe_allow_html=True)


def render_score_header(score: int, streak: int, accuracy: float):
    """Render the score header during a quiz."""
    cols = st.columns(3)
    with cols[0]:
        st.markdown(f"""
            <div class="stat-box">
                <div class="stat-value">{score}</div>
                <div class="stat-label">Score</div>
            </div>
        """, unsafe_allow_html=True)
    with cols[1]:
        st.markdown(f"""
            <div class="stat-box">
                <div class="stat-value" style="color: {THEME['secondary']};">{'🔥 ' if streak > 1 else ''}{streak}</div>
                <div class="stat-label">Streak</div>
            </div>
        """, unsafe_allow_html=True)
    with cols[2]:
        st.markdown(f"""
            <div class="stat-box">
                <div class="stat-value" style="color: {THEME['accent']};">{accuracy}%</div>
                <div class="stat-label">Accuracy</div>
            </div>
        """, unsafe_allow_html=True)


def render_session_summary(summary: dict):
    """Render the end-of-session summary."""
    score = summary.get("score", 0)
    accuracy = summary.get("accuracy", 0)
    best_streak = summary.get("best_streak", 0)
    diff_reached = summary.get("difficulty_reached", 1)
    questions = summary.get("questions_answered", 0)
    correct = summary.get("correct_answers", 0)
    avg_time = summary.get("avg_time_per_question", 0)

    diff_label, diff_emoji = DIFFICULTY_LABELS.get(diff_reached, ("Medium", "🟡"))

    # Grade
    if accuracy >= 90:
        grade, grade_color = "S", "#FFD700"
    elif accuracy >= 75:
        grade, grade_color = "A", THEME['success']
    elif accuracy >= 60:
        grade, grade_color = "B", THEME['accent']
    elif accuracy >= 40:
        grade, grade_color = "C", THEME['warning']
    else:
        grade, grade_color = "D", THEME['error']

    st.markdown(f"""
        <div style="text-align: center; padding: 30px 0;">
            <div style="font-size: 3.5rem; margin-bottom: 10px;">🏆</div>
            <div class="hero-title" style="font-size: 2rem;">Quiz Complete!</div>
            <div class="score-display">{score} pts</div>
            <div style="margin: 16px 0;">
                <span style="font-size: 3rem; font-weight: 800; color: {grade_color};">{grade}</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

    cols = st.columns(4)
    stats_data = [
        (f"{correct}/{questions}", "Correct"),
        (f"{accuracy}%", "Accuracy"),
        (f"🔥 {best_streak}", "Best Streak"),
        (f"{diff_emoji} {diff_label}", "Max Difficulty"),
    ]
    for col, (val, label) in zip(cols, stats_data):
        with col:
            st.markdown(f"""
                <div class="stat-box">
                    <div class="stat-value" style="font-size: 1.4rem;">{val}</div>
                    <div class="stat-label">{label}</div>
                </div>
            """, unsafe_allow_html=True)


def render_leaderboard(entries: list, title: str = "🏆 Leaderboard"):
    """Render a leaderboard table."""
    st.markdown(f"### {title}")

    if not entries:
        st.markdown(f"""
            <div class="trivia-card" style="text-align: center; color: {THEME['text_secondary']};">
                No scores yet — be the first to play!
            </div>
        """, unsafe_allow_html=True)
        return

    for i, entry in enumerate(entries):
        rank = i + 1
        if rank == 1:
            rank_class = "lb-gold"
            rank_display = "🥇"
        elif rank == 2:
            rank_class = "lb-silver"
            rank_display = "🥈"
        elif rank == 3:
            rank_class = "lb-bronze"
            rank_display = "🥉"
        else:
            rank_class = ""
            rank_display = f"#{rank}"

        username = entry.get("username", "Anonymous")
        score = entry.get("score", 0)
        accuracy = entry.get("accuracy", 0)
        mode_key = entry.get("mode", "quiz")
        mode_name = GAME_MODES.get(mode_key, {}).get("name", mode_key)

        st.markdown(f"""
            <div class="lb-row">
                <span class="lb-rank {rank_class}" style="font-size: 1.2rem;">{rank_display}</span>
                <span style="flex: 1; padding-left: 12px; font-weight: 500;">{username}</span>
                <span style="color: {THEME['primary']}; font-weight: 700; margin-right: 16px;">{score} pts</span>
                <span style="color: {THEME['text_secondary']}; font-size: 0.85rem;">{accuracy}%</span>
            </div>
        """, unsafe_allow_html=True)


def render_stats_charts(stats: dict):
    """Render statistics charts using Plotly."""
    # ── Topic Performance Radar Chart ──
    topic_data = stats.get("topic_performance", [])
    if topic_data:
        st.markdown("### 📊 Topic Performance")
        categories = [d["topic"] for d in topic_data]
        values = [d["accuracy"] for d in topic_data]

        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(
            r=values + [values[0]] if values else [],
            theta=categories + [categories[0]] if categories else [],
            fill='toself',
            fillcolor='rgba(108, 99, 255, 0.15)',
            line=dict(color=THEME['primary'], width=2),
            marker=dict(size=8, color=THEME['primary']),
        ))
        fig.update_layout(
            polar=dict(
                bgcolor='rgba(0,0,0,0)',
                radialaxis=dict(
                    visible=True, range=[0, 100],
                    gridcolor='rgba(255,255,255,0.06)',
                    tickfont=dict(color=THEME['text_secondary']),
                ),
                angularaxis=dict(
                    gridcolor='rgba(255,255,255,0.06)',
                    tickfont=dict(color=THEME['text_primary'], size=12),
                ),
            ),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            showlegend=False,
            margin=dict(l=60, r=60, t=30, b=30),
            height=350,
        )
        st.plotly_chart(fig, use_container_width=True)

    # ── Score Progress Chart ──
    recent = stats.get("recent_sessions", [])
    if recent:
        st.markdown("### 📈 Score History")
        recent_reversed = list(reversed(recent))
        scores = [s["score"] for s in recent_reversed]
        labels = [f"Game {i+1}" for i in range(len(recent_reversed))]

        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(
            x=labels, y=scores,
            mode='lines+markers',
            line=dict(color=THEME['primary'], width=3, shape='spline'),
            marker=dict(size=8, color=THEME['primary'],
                       line=dict(width=2, color='white')),
            fill='tonexty',
            fillcolor='rgba(108, 99, 255, 0.08)',
        ))
        fig2.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            xaxis=dict(
                gridcolor='rgba(255,255,255,0.04)',
                tickfont=dict(color=THEME['text_secondary']),
            ),
            yaxis=dict(
                gridcolor='rgba(255,255,255,0.06)',
                tickfont=dict(color=THEME['text_secondary']),
                title="Score",
                title_font=dict(color=THEME['text_secondary']),
            ),
            margin=dict(l=40, r=20, t=20, b=40),
            height=300,
        )
        st.plotly_chart(fig2, use_container_width=True)


def render_sidebar_user_info(username: str, stats: dict):
    """Render user info in sidebar."""
    total_sessions = stats.get("total_sessions", 0)
    total_score = stats.get("total_score", 0)
    avg_accuracy = stats.get("avg_accuracy", 0)
    max_diff = stats.get("max_difficulty", 1)
    diff_label, diff_emoji = DIFFICULTY_LABELS.get(max_diff, ("Beginner", "🟢"))

    st.sidebar.markdown(f"""
        <div class="trivia-card" style="margin: 0;">
            <div style="font-size: 1.5rem; margin-bottom: 4px;">👤 {username}</div>
            <div style="color: {THEME['text_secondary']}; font-size: 0.85rem; margin-bottom: 16px;">
                {total_sessions} games played
            </div>
            <div style="display: flex; justify-content: space-between;">
                <div style="text-align: center;">
                    <div style="font-weight: 700; color: {THEME['primary']};">{total_score}</div>
                    <div style="font-size: 0.75rem; color: {THEME['text_secondary']};">Total Score</div>
                </div>
                <div style="text-align: center;">
                    <div style="font-weight: 700; color: {THEME['accent']};">{round(avg_accuracy, 1)}%</div>
                    <div style="font-size: 0.75rem; color: {THEME['text_secondary']};">Avg Accuracy</div>
                </div>
                <div style="text-align: center;">
                    <div style="font-weight: 700; color: {THEME['secondary']};">{diff_emoji}</div>
                    <div style="font-size: 0.75rem; color: {THEME['text_secondary']};">Max Level</div>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)
