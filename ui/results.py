"""Results and detailed question-by-question review with AI feedback and retry flow."""
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from models.schemas import AIFeedback, QuestionItem, QuestionReviewItem, QuizResult, TopicPerformance
from repositories.quiz_repository import QuizRepository
from services.feedback_service import FeedbackService
from ui.components import render_hero_banner, render_metric_card


def render_results_page(quiz_repo: QuizRepository, feedback_service: FeedbackService):
    """Render comprehensive score analytics, AI revision roadmap, and answer breakdown."""
    # Check if viewing a specific past attempt or latest result
    result: QuizResult = None
    feedback: AIFeedback = None

    if st.session_state.get("view_attempt_id"):
        attempt_id = st.session_state["view_attempt_id"]
        attempt_data = quiz_repo.get_attempt(attempt_id)
        if attempt_data:
            # Reconstruct result object
            reviews = [
                QuestionReviewItem(
                    question_id=q["question_id"],
                    question=q["question"],
                    options=q["options"],
                    selected_answer=q["selected_answer"],
                    correct_answer=q["correct_answer"],
                    is_correct=q["is_correct"],
                    is_unanswered=q["is_unanswered"],
                    explanation=q["explanation"],
                    mistake_analysis=f"Selected: {q['selected_answer']}, Correct: {q['correct_answer']}" if not q["is_correct"] and not q["is_unanswered"] else None,
                    topic=q["topic"],
                    difficulty=q["difficulty"],
                    source_reference=q["source_reference"],
                )
                for q in attempt_data["questions"]
            ]

            topic_breakdowns = [
                TopicPerformance(**t) for t in attempt_data.get("topic_breakdowns", [])
            ]

            time_sec = attempt_data["time_taken_seconds"]
            m = time_sec // 60
            s = time_sec % 60
            time_fmt = f"{m}m {s}s" if m > 0 else f"{s}s"

            result = QuizResult(
                attempt_id=attempt_id,
                quiz_id=attempt_data["quiz_id"],
                total_questions=attempt_data["total_questions"],
                correct_count=attempt_data["correct_count"],
                incorrect_count=attempt_data["incorrect_count"],
                unanswered_count=attempt_data["unanswered_count"],
                score_percentage=attempt_data["score_percentage"],
                accuracy_rate=attempt_data["accuracy_rate"],
                time_taken_seconds=time_sec,
                time_taken_formatted=time_fmt,
                performance_grade=attempt_data["performance_grade"],
                summary_message=f"Historical attempt record for {attempt_data['document_name']}",
                topic_breakdowns=topic_breakdowns,
                reviews=reviews,
            )

            if attempt_data.get("ai_feedback"):
                feedback = AIFeedback(**attempt_data["ai_feedback"])
            else:
                feedback = feedback_service.generate_fallback_feedback(result)

    elif st.session_state.get("latest_result"):
        result = st.session_state["latest_result"]
        feedback = st.session_state.get("latest_feedback")
        if not feedback:
            feedback = feedback_service.generate_fallback_feedback(result)

    if not result:
        st.info("ℹ️ No quiz results to display yet. Complete a quiz to view your performance report.")
        if st.button("🚀 Start a Quiz", type="primary"):
            st.session_state["active_nav"] = "Create Quiz"
            st.rerun()
        return

    # Hero Banner
    grade_color = "#22c55e" if result.score_percentage >= 80 else ("#eab308" if result.score_percentage >= 60 else "#ef4444")
    render_hero_banner(
        title=f"Assessment Report • Score: {result.score_percentage}%",
        subtitle=result.summary_message,
        badge=f"GRADE: {result.performance_grade}",
    )

    # Top Metric Cards
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        render_metric_card("Final Score", f"{result.score_percentage}%", f"{result.correct_count} of {result.total_questions} correct", "🎯")
    with c2:
        render_metric_card("Accuracy Rate", f"{result.accuracy_rate}%", "On attempted questions", "✅")
    with c3:
        render_metric_card("Time Taken", result.time_taken_formatted, "Total test duration", "⏱️")
    with c4:
        render_metric_card("Questions Missed", f"{result.incorrect_count + result.unanswered_count}", f"{result.incorrect_count} wrong, {result.unanswered_count} skipped", "❌")

    st.write("")

    # Visual Analytics Row: Score Donut Chart + Topic Mastery Bar Chart
    g_col1, g_col2 = st.columns([2, 3])

    with g_col1:
        st.subheader("📊 Breakdown")
        donut_fig = go.Figure(
            data=[
                go.Pie(
                    labels=["Correct", "Incorrect", "Unanswered"],
                    values=[result.correct_count, result.incorrect_count, result.unanswered_count],
                    hole=0.6,
                    marker=dict(colors=["#22c55e", "#ef4444", "#f59e0b"]),
                )
            ]
        )
        donut_fig.update_layout(
            margin=dict(l=10, r=10, t=10, b=10),
            height=250,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#cbd5e1"),
            showlegend=True,
        )
        st.plotly_chart(donut_fig, use_container_width=True)

    with g_col2:
        st.subheader("📌 Topic-Level Accuracy")
        if result.topic_breakdowns:
            topics = [t.topic for t in result.topic_breakdowns]
            accuracies = [t.accuracy_percentage for t in result.topic_breakdowns]
            colors = ["#22c55e" if acc >= 75 else ("#eab308" if acc >= 50 else "#ef4444") for acc in accuracies]

            bar_fig = go.Figure(
                data=[
                    go.Bar(
                        x=accuracies,
                        y=topics,
                        orientation="h",
                        marker=dict(color=colors),
                        text=[f"{acc:.0f}%" for acc in accuracies],
                        textposition="outside",
                    )
                ]
            )
            bar_fig.update_layout(
                margin=dict(l=10, r=20, t=10, b=10),
                height=250,
                xaxis=dict(range=[0, 115], title="Accuracy (%)", gridcolor="rgba(255,255,255,0.08)"),
                yaxis=dict(gridcolor="rgba(255,255,255,0.08)"),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#cbd5e1"),
            )
            st.plotly_chart(bar_fig, use_container_width=True)
        else:
            st.info("No topic breakdown data available.")

    st.divider()

    # Retry Incorrect Questions Button
    missed_reviews = [r for r in result.reviews if not r.is_correct]
    if missed_reviews:
        r_col1, r_col2 = st.columns([3, 1])
        with r_col1:
            st.info(f"💡 You missed or skipped **{len(missed_reviews)} question(s)**. You can launch a targeted revision quiz featuring only these questions.")
        with r_col2:
            if st.button("🔁 Retry Missed Questions", type="primary", use_container_width=True):
                # Construct fresh quiz with only missed questions
                quiz_data = quiz_repo.get_quiz_with_questions(result.quiz_id)
                doc_name = quiz_data["document_name"] if quiz_data else "Review Quiz"

                retry_questions = []
                for r in missed_reviews:
                    retry_questions.append({
                        "question_id": r.question_id,
                        "question": r.question,
                        "options": r.options,
                        "correct_answer": r.correct_answer,
                        "explanation": r.explanation,
                        "topic": r.topic,
                        "difficulty": r.difficulty,
                        "source_reference": r.source_reference,
                    })

                st.session_state["active_quiz"] = {
                    "quiz_id": result.quiz_id,
                    "document_name": f"{doc_name} (Retry Missed)",
                    "difficulty": "Targeted Retry",
                    "question_count": len(retry_questions),
                    "questions": retry_questions,
                    "time_limit_minutes": None,
                }
                st.session_state["quiz_answers"] = {}
                st.session_state["quiz_marked"] = set()
                st.session_state["current_question_idx"] = 0
                st.session_state["quiz_start_timestamp"] = None
                st.session_state["active_nav"] = "Take Quiz"
                st.rerun()

    # Learning Feedback Section
    st.subheader("💡 Personalized Performance Feedback & Study Plan")
    with st.container():
        f1, f2 = st.columns([1, 1])
        with f1:
            st.markdown(f"**Overall Assessment:**\n\n{feedback.overall_assessment}")
            st.markdown("**🌟 Strongest Topics:**")
            for t in feedback.strongest_topics:
                st.markdown(f"- ✅ {t}")

            st.markdown("**⚠️ Topics Needing Review:**")
            for t in feedback.weak_topics:
                st.markdown(f"- 🔍 {t}")

        with f2:
            st.markdown("**📋 Prioritized Revision Plan:**")
            for step in feedback.prioritized_revision_plan:
                st.markdown(f"- {step}")

            st.markdown("**💡 Suggested Follow-Up Activities:**")
            for act in feedback.suggested_follow_up_activities:
                st.markdown(f"- ✍️ {act}")

        st.info(f"💪 **Encouragement:** {feedback.encouragement}")

    st.divider()

    # Detailed Question-by-Question Review Section
    st.subheader("📝 Detailed Question-by-Question Review")

    # Filter selector
    filter_option = st.radio(
        "Filter Questions:",
        options=["All Questions", "Correct Only", "Incorrect Only", "Unanswered Only"],
        horizontal=True,
    )

    filtered_reviews = result.reviews
    if filter_option == "Correct Only":
        filtered_reviews = [r for r in result.reviews if r.is_correct]
    elif filter_option == "Incorrect Only":
        filtered_reviews = [r for r in result.reviews if not r.is_correct and not r.is_unanswered]
    elif filter_option == "Unanswered Only":
        filtered_reviews = [r for r in result.reviews if r.is_unanswered]

    st.caption(f"Showing {len(filtered_reviews)} of {result.total_questions} questions:")

    for r in filtered_reviews:
        # Determine container card styling
        if r.is_correct:
            card_class = "review-correct"
            status_badge = "✅ Correct"
            badge_color = "#22c55e"
        elif r.is_unanswered:
            card_class = "review-unanswered"
            status_badge = "⚠️ Unanswered"
            badge_color = "#f59e0b"
        else:
            card_class = "review-incorrect"
            status_badge = "❌ Incorrect"
            badge_color = "#ef4444"

        with st.container():
            st.markdown(
                f"""
                <div class="review-card {card_class}">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                        <span style="font-weight:700; color:#f8fafc;">{r.question_id} • {r.topic}</span>
                        <span style="background:rgba(255,255,255,0.1); color:{badge_color}; font-weight:700; font-size:0.8rem; padding:2px 10px; border-radius:6px;">
                            {status_badge}
                        </span>
                    </div>
                    <div style="font-size:1.05rem; font-weight:600; color:#ffffff; margin-bottom:12px;">{r.question}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Display options with highlights
            for opt_key in ["A", "B", "C", "D"]:
                opt_text = r.options.get(opt_key, "")
                if opt_key == r.correct_answer:
                    st.markdown(
                        f"<div class='option-item option-correct-highlight'><b>{opt_key}:</b> {opt_text} (Correct Answer)</div>",
                        unsafe_allow_html=True,
                    )
                elif opt_key == r.selected_answer and not r.is_correct:
                    st.markdown(
                        f"<div class='option-item option-wrong-highlight'><b>{opt_key}:</b> {opt_text} (Your Selection)</div>",
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        f"<div class='option-item option-normal'><b>{opt_key}:</b> {opt_text}</div>",
                        unsafe_allow_html=True,
                    )

            # Explanation and Mistake note
            st.markdown(f"**📖 Explanation:** {r.explanation}")
            if r.mistake_analysis:
                st.markdown(f"**💡 Mistake Analysis:** {r.mistake_analysis}")
            if r.source_reference:
                st.caption(f"Source Reference: {r.source_reference}")

            st.write("")
