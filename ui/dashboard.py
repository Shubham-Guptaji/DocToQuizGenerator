"""Home Dashboard view displaying metrics, progression charts, and recent activity."""
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from config.settings import settings
from repositories.quiz_repository import QuizRepository
from ui.components import render_hero_banner, render_metric_card


def render_dashboard_page(quiz_repo: QuizRepository):
    """Render the main home dashboard overview."""
    render_hero_banner(
        title="Smart Quiz & Assessment Platform",
        subtitle="Transform any educational PDF into challenging exam-style MCQs with automated scoring and personalized AI revision roadmaps.",
        badge="STUDENT & ASPIRANT DASHBOARD",
    )

    # API Key status warning if missing
    if not settings.has_gemini_api_key:
        st.warning(
            "⚠️ **Gemini API Key Not Configured**: Running in **Local Mock Provider Mode**. "
            "Questions and feedback will be generated using realistic local mock data. "
            "To connect live Google Gemini 3.8 Flash, enter your API key in **⚙️ Settings** or in `.env`."
        )

    # Fetch stats
    stats = quiz_repo.get_dashboard_stats()
    total_quizzes = stats["total_quizzes"]
    avg_score = stats["average_score"]
    best_score = stats["best_score"]
    recent_attempts = stats["recent_attempts"]

    # Top CTA Bar
    col_cta1, col_cta2 = st.columns([3, 1])
    with col_cta1:
        st.write("Ready to test your knowledge or prepare for an upcoming examination?")
    with col_cta2:
        if st.button("🚀 Create New Quiz", type="primary", use_container_width=True):
            st.session_state["active_nav"] = "Create Quiz"
            st.rerun()

    st.write("")

    # Metric Cards Row
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        render_metric_card("Total Completed", f"{total_quizzes}", "Across all documents", "📚")
    with m2:
        render_metric_card("Average Score", f"{avg_score}%", "Overall performance", "📊")
    with m3:
        render_metric_card("Best Score", f"{best_score}%", "Personal best record", "🏆")
    with m4:
        recent_count = len(recent_attempts)
        render_metric_card("Recent Activity", f"{recent_count}", "Last 5 attempts", "⏱️")

    st.divider()

    # Progress Charts Section
    if total_quizzes > 0:
        c_left, c_right = st.columns([3, 2])

        with c_left:
            st.subheader("📈 Score Progression Over Time")
            # Retrieve all attempts chronologically for plotting
            all_attempts = quiz_repo.get_all_attempts(limit=30)
            all_attempts_sorted = sorted(all_attempts, key=lambda x: x["completed_at"])

            dates = [a["completed_at"].strftime("%b %d, %H:%M") for a in all_attempts_sorted]
            scores = [a["score_percentage"] for a in all_attempts_sorted]
            labels = [f"{a['document_name'][:20]}... ({a['difficulty']})" for a in all_attempts_sorted]

            fig = go.Figure()
            fig.add_trace(
                go.Scatter(
                    x=dates,
                    y=scores,
                    mode="lines+markers",
                    name="Score %",
                    line=dict(color="#6366f1", width=3),
                    marker=dict(size=8, color="#818cf8"),
                    text=labels,
                    hovertemplate="<b>%{text}</b><br>Date: %{x}<br>Score: %{y:.1f}%<extra></extra>",
                )
            )
            # Add mastery target reference line at 80%
            fig.add_hline(
                y=80,
                line_dash="dot",
                line_color="#22c55e",
                annotation_text="Mastery Goal (80%)",
                annotation_position="bottom right",
            )
            fig.update_layout(
                margin=dict(l=20, r=20, t=20, b=20),
                height=300,
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                yaxis=dict(range=[0, 105], title="Score (%)", gridcolor="rgba(255,255,255,0.08)"),
                xaxis=dict(gridcolor="rgba(255,255,255,0.08)"),
                font=dict(color="#cbd5e1"),
            )
            st.plotly_chart(fig, use_container_width=True)

        with c_right:
            st.subheader("🎯 Difficulty Distribution")
            diff_counts = {"Easy": 0, "Medium": 0, "Hard": 0, "Mixed": 0}
            for a in all_attempts:
                d = a.get("difficulty", "Medium")
                diff_counts[d] = diff_counts.get(d, 0) + 1

            diff_fig = px.pie(
                values=list(diff_counts.values()),
                names=list(diff_counts.keys()),
                color=list(diff_counts.keys()),
                color_discrete_map={
                    "Easy": "#22c55e",
                    "Medium": "#eab308",
                    "Hard": "#ef4444",
                    "Mixed": "#6366f1",
                },
                hole=0.45,
            )
            diff_fig.update_layout(
                margin=dict(l=10, r=10, t=10, b=10),
                height=300,
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#cbd5e1"),
                showlegend=True,
            )
            st.plotly_chart(diff_fig, use_container_width=True)

        st.subheader("🕒 Recent Quiz Attempts")
        for att in recent_attempts:
            with st.container():
                col_info, col_score, col_act = st.columns([4, 2, 2])
                with col_info:
                    st.markdown(f"**📄 {att['document_name']}**")
                    time_str = att["completed_at"].strftime("%Y-%m-%d %H:%M")
                    st.caption(f"Completed on {time_str} • Difficulty: {att['difficulty']} • {att['total_questions']} Questions")
                with col_score:
                    score = att["score_percentage"]
                    grade = att["performance_grade"]
                    color = "#22c55e" if score >= 80 else ("#eab308" if score >= 60 else "#ef4444")
                    st.markdown(f"<span style='font-size:1.3rem; font-weight:700; color:{color};'>{score}%</span> ({grade})", unsafe_allow_html=True)
                with col_act:
                    if st.button("🔍 Review Results", key=f"dash_rev_{att['attempt_id']}"):
                        st.session_state["view_attempt_id"] = att["attempt_id"]
                        st.session_state["active_nav"] = "Results & Review"
                        st.rerun()
                st.divider()

    else:
        st.info("👋 You haven't taken any quizzes yet! Upload a PDF to generate your first custom quiz.")
        col_empty1, col_empty2, col_empty3 = st.columns(3)
        with col_empty1:
            st.markdown("### 1. Upload PDF")
            st.write("Upload course slides, textbooks, lecture notes, or research papers.")
        with col_empty2:
            st.markdown("### 2. Configure & Generate")
            st.write("Pick your difficulty (Easy, Medium, Hard, Mixed) and target question count (10-50).")
        with col_empty3:
            st.markdown("### 3. Review & Learn")
            st.write("Receive instant deterministic scoring, mistake explanations, and an AI revision roadmap.")
