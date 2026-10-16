"""Quiz History view for browsing past attempts, reviewing results, and managing records."""
import streamlit as st
from repositories.quiz_repository import QuizRepository
from ui.components import render_hero_banner


def render_history_page(quiz_repo: QuizRepository):
    """Render historical quiz attempts table with review and deletion controls."""
    render_hero_banner(
        title="Quiz History & Performance Records",
        subtitle="Review past examination attempts, track progress over time, or clean up saved assessments.",
        badge="PERSISTENCE & RETENTION",
    )

    attempts = quiz_repo.get_all_attempts(limit=100)

    if not attempts:
        st.info("ℹ️ No quiz attempts recorded yet. Take a quiz to populate your history log.")
        if st.button("🚀 Create New Quiz", type="primary"):
            st.session_state["active_nav"] = "Create Quiz"
            st.rerun()
        return

    # Top Action Bar: Search and Clear History
    col_search, col_clear = st.columns([3, 1])
    with col_search:
        search_query = st.text_input("🔍 Search by Document Name:", placeholder="Filter by document title...")
    with col_clear:
        st.write("")
        if st.button("🗑️ Clear All History", type="secondary", use_container_width=True):
            st.session_state["confirm_clear_all"] = True

    # Confirm clear all dialog
    if st.session_state.get("confirm_clear_all"):
        st.warning("⚠️ Are you sure you want to permanently delete all quiz attempts, questions, and uploaded document records?")
        c_yes, c_no = st.columns(2)
        with c_yes:
            if st.button("Yes, Clear Everything", type="primary"):
                quiz_repo.clear_all_history()
                st.session_state["confirm_clear_all"] = False
                st.success("All quiz history cleared.")
                st.rerun()
        with c_no:
            if st.button("Cancel"):
                st.session_state["confirm_clear_all"] = False
                st.rerun()

    # Filter attempts
    filtered = attempts
    if search_query.strip():
        filtered = [a for a in attempts if search_query.lower() in a["document_name"].lower()]

    st.write(f"Showing **{len(filtered)}** attempt(s):")

    for att in filtered:
        with st.container():
            col_d, col_m, col_s, col_actions = st.columns([3, 2, 2, 2])
            with col_d:
                st.markdown(f"**📄 {att['document_name']}**")
                date_str = att["completed_at"].strftime("%Y-%m-%d %H:%M")
                st.caption(f"Completed: {date_str}")
            with col_m:
                st.write(f"**Difficulty:** `{att['difficulty']}`")
                st.caption(f"{att['total_questions']} Questions")
            with col_s:
                score = att["score_percentage"]
                grade = att["performance_grade"]
                color = "#22c55e" if score >= 80 else ("#eab308" if score >= 60 else "#ef4444")
                st.markdown(f"<span style='font-size:1.2rem; font-weight:700; color:{color};'>{score}%</span> ({grade})", unsafe_allow_html=True)
                st.caption(f"{att['correct_count']}/{att['total_questions']} correct")
            with col_actions:
                col_btn_rev, col_btn_del = st.columns(2)
                with col_btn_rev:
                    if st.button("🔍 Review", key=f"hist_rev_{att['attempt_id']}"):
                        st.session_state["view_attempt_id"] = att["attempt_id"]
                        st.session_state["active_nav"] = "Results & Review"
                        st.rerun()
                with col_btn_del:
                    if st.button("🗑️", key=f"hist_del_{att['attempt_id']}", help="Delete this attempt"):
                        quiz_repo.delete_attempt(att["attempt_id"])
                        st.rerun()
            st.divider()
