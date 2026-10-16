"""Interactive quiz-taking interface with navigation, answer selection, and submission controls."""
import time
import streamlit as st
from models.schemas import QuestionItem, QuizSubmission
from repositories.quiz_repository import QuizRepository
from services.feedback_service import FeedbackService
from services.scoring_service import ScoringService


def render_take_quiz_page(
    quiz_repo: QuizRepository,
    scoring_service: ScoringService,
    feedback_service: FeedbackService,
):
    """Render the active quiz-taking view."""
    active_quiz = st.session_state.get("active_quiz")
    if not active_quiz:
        st.info("ℹ️ No active quiz session found. Please generate or select a quiz first.")
        if st.button("🚀 Go to Create Quiz", type="primary"):
            st.session_state["active_nav"] = "Create Quiz"
            st.rerun()
        return

    # Track start time
    if st.session_state.get("quiz_start_timestamp") is None:
        st.session_state["quiz_start_timestamp"] = time.time()

    elapsed_seconds = int(time.time() - st.session_state["quiz_start_timestamp"])

    questions_raw = active_quiz["questions"]
    total_q = len(questions_raw)
    current_idx = st.session_state.get("current_question_idx", 0)

    # Bound safety
    current_idx = max(0, min(current_idx, total_q - 1))
    st.session_state["current_question_idx"] = current_idx

    current_q_data = questions_raw[current_idx]
    current_q_id = current_q_data["question_id"]

    # Answers & flags state
    answers_dict = st.session_state.setdefault("quiz_answers", {})
    marked_set = st.session_state.setdefault("quiz_marked", set())

    answered_count = len([k for k, v in answers_dict.items() if v])
    unanswered_count = total_q - answered_count
    progress_ratio = answered_count / total_q if total_q > 0 else 0.0

    # Top Status & Timer Bar
    col_t1, col_t2, col_t3, col_t4 = st.columns([3, 2, 2, 2])
    with col_t1:
        st.markdown(f"**📄 Document:** {active_quiz['document_name'][:28]}...")
    with col_t2:
        st.markdown(f"**Difficulty:** `{active_quiz['difficulty']}`")
    with col_t3:
        st.markdown(f"**Answered:** {answered_count}/{total_q} ({unanswered_count} left)")
    with col_t4:
        # Timer display
        time_limit_min = active_quiz.get("time_limit_minutes")
        if time_limit_min:
            remaining = max(0, (time_limit_min * 60) - elapsed_seconds)
            rem_m = remaining // 60
            rem_s = remaining % 60
            timer_color = "#ef4444" if remaining < 120 else "#22c55e"
            st.markdown(f"⏱️ **Time Left:** <span style='color:{timer_color}; font-weight:700;'>{rem_m:02d}:{rem_s:02d}</span>", unsafe_allow_html=True)
        else:
            el_m = elapsed_seconds // 60
            el_s = elapsed_seconds % 60
            st.markdown(f"⏱️ **Elapsed:** `{el_m:02d}:{el_s:02d}`")

    # Progress Bar
    st.progress(progress_ratio)

    st.write("")

    # Main Quiz Grid: Left Column Question Card, Right Column Question Palette Navigator
    col_main, col_palette = st.columns([3, 1])

    with col_main:
        # Question Header Badges
        diff_cls = f"diff-{current_q_data.get('difficulty', 'medium').lower()}"
        topic_name = current_q_data.get("topic", "General")
        page_ref = current_q_data.get("source_reference", "")

        badges_html = (
            f"<span class='question-number-badge'>Question {current_idx + 1} of {total_q}</span>"
            f"<span class='question-topic-badge'>📌 {topic_name}</span>"
            f"<span class='question-difficulty-badge {diff_cls}'>{current_q_data.get('difficulty', 'Medium')}</span>"
        )
        if page_ref:
            badges_html += f"<span class='question-topic-badge'>📖 {page_ref}</span>"

        st.markdown(badges_html, unsafe_allow_html=True)

        # Question Text
        st.markdown(f"<div class='question-text'>{current_q_data['question']}</div>", unsafe_allow_html=True)

        # Options Radio Selector
        options = current_q_data["options"]  # {"A": "...", "B": "...", ...}
        option_keys = ["A", "B", "C", "D"]
        option_display_list = [f"{k}: {options[k]}" for k in option_keys]

        # Determine currently selected radio index
        current_selection = answers_dict.get(current_q_id)
        current_index = None
        if current_selection in option_keys:
            current_index = option_keys.index(current_selection)

        selected_radio = st.radio(
            "Select your answer:",
            options=option_display_list,
            index=current_index,
            key=f"radio_q_{current_q_id}_{current_idx}",
            label_visibility="collapsed",
        )

        # Update answer when user selects
        if selected_radio:
            chosen_key = selected_radio.split(":")[0].strip()
            answers_dict[current_q_id] = chosen_key
        else:
            if current_q_id in answers_dict:
                del answers_dict[current_q_id]

        st.write("")

        # Navigation & Mark for Review Controls
        nav_prev, nav_mark, nav_clear, nav_next = st.columns([1, 1.2, 1, 1])

        with nav_prev:
            if st.button("⬅️ Previous", disabled=(current_idx == 0), use_container_width=True):
                st.session_state["current_question_idx"] = current_idx - 1
                st.rerun()

        with nav_mark:
            is_marked = current_q_id in marked_set
            mark_label = "🚩 Unmark Review" if is_marked else "🏳️ Mark for Review"
            if st.button(mark_label, use_container_width=True):
                if is_marked:
                    marked_set.remove(current_q_id)
                else:
                    marked_set.add(current_q_id)
                st.rerun()

        with nav_clear:
            if st.button("🔄 Clear", use_container_width=True):
                if current_q_id in answers_dict:
                    del answers_dict[current_q_id]
                st.rerun()

        with nav_next:
            if current_idx < total_q - 1:
                if st.button("Next ➡️", type="primary", use_container_width=True):
                    st.session_state["current_question_idx"] = current_idx + 1
                    st.rerun()
            else:
                st.caption("Last Question")

    with col_palette:
        st.markdown("### Question Palette")
        st.caption("Click any number to jump directly:")

        # Palette Grid: 5 columns
        cols = st.columns(5)
        for i in range(total_q):
            q_item = questions_raw[i]
            qid = q_item["question_id"]
            is_ans = qid in answers_dict and answers_dict[qid]
            is_m = qid in marked_set
            is_curr = i == current_idx

            # Palette button label
            label = f"{i+1}"
            if is_m:
                label += "🚩"
            elif is_ans:
                label += "✓"

            col_target = cols[i % 5]
            btn_type = "primary" if is_curr else ("secondary")
            if col_target.button(label, key=f"pal_btn_{i}", type=btn_type, use_container_width=True):
                st.session_state["current_question_idx"] = i
                st.rerun()

        st.markdown(
            """
            <div style="font-size:0.75rem; color:#94a3b8; margin-top:10px;">
                <b>Legend:</b><br>
                • <b>✓</b> Answered<br>
                • <b>🚩</b> Marked for review<br>
                • <b>Active</b> Highlighted in blue
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.divider()

    # Submit Section with Confirmation
    col_sub_info, col_sub_btn = st.columns([3, 1])

    with col_sub_info:
        if unanswered_count > 0:
            st.warning(f"⚠️ You still have **{unanswered_count} unanswered question(s)**. You may review them before submitting.")
        else:
            st.success("🎉 All questions answered! You are ready to submit.")

    with col_sub_btn:
        submit_btn = st.button("📥 Submit Quiz", type="primary", use_container_width=True)

    if submit_btn:
        # Prevent double submit
        if st.session_state.get("is_submitting"):
            return
        st.session_state["is_submitting"] = True

        with st.spinner("Scoring assessment and generating personalized AI learning feedback..."):
            # Construct submission
            submission = QuizSubmission(
                quiz_id=active_quiz["quiz_id"],
                time_taken_seconds=elapsed_seconds,
                answers=answers_dict,
            )

            # Reconstruct QuestionItem models for deterministic scoring
            question_objs = [QuestionItem(**q) for q in questions_raw]
            result = scoring_service.score_quiz(question_objs, submission)

            # Generate feedback
            feedback = feedback_service.generate_feedback(result)

            # Persist to database
            attempt_id = quiz_repo.save_quiz_attempt(
                quiz_id=active_quiz["quiz_id"],
                result=result,
                ai_feedback_dict=feedback.model_dump(),
            )
            result.attempt_id = attempt_id

            # Save to session and switch to results view
            st.session_state["latest_result"] = result
            st.session_state["latest_feedback"] = feedback
            st.session_state["active_nav"] = "Results & Review"
            st.session_state["is_submitting"] = False
            # Clear active quiz from in-progress taking
            st.session_state["active_quiz"] = None
            st.session_state["quiz_answers"] = {}
            st.session_state["quiz_marked"] = set()
            st.rerun()
