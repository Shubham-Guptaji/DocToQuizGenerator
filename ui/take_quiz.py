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
        st.info("ℹ️ No active quiz session in progress.")
        available = quiz_repo.get_available_quizzes(limit=5)
        if available:
            st.markdown("### 📚 Select a Quiz to Practice:")
            for qz in available:
                with st.container():
                    c_info, c_btn = st.columns([3, 1])
                    with c_info:
                        st.markdown(f"**📄 {qz['document_name']}**")
                        st.caption(f"{qz['question_count']} Questions • Difficulty: {qz['difficulty']}")
                    with c_btn:
                        if st.button("▶️ Start Quiz", key=f"start_avail_{qz['quiz_id']}", type="primary", use_container_width=True):
                            loaded = quiz_repo.get_quiz_with_questions(qz["quiz_id"])
                            if loaded:
                                st.session_state["active_quiz"] = {
                                    "quiz_id": loaded["id"],
                                    "document_name": loaded["document_name"],
                                    "difficulty": loaded["difficulty"],
                                    "question_count": len(loaded["questions"]),
                                    "questions": [q.model_dump() for q in loaded["questions"]],
                                    "time_limit_minutes": None,
                                }
                                st.session_state["quiz_answers"] = {}
                                st.session_state["quiz_marked"] = set()
                                st.session_state["current_question_idx"] = 0
                                st.session_state["quiz_start_timestamp"] = None
                                st.rerun()

        st.write("")
        if st.button("🚀 Create New Quiz from PDF", type="secondary" if available else "primary"):
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
        # Question state counts
        rev_count = len([q for q in questions_raw if q["question_id"] in marked_set])
        att_count = len([q for q in questions_raw if q["question_id"] in answers_dict and answers_dict[q["question_id"]] and q["question_id"] not in marked_set])
        unatt_count = total_q - (att_count + rev_count)

        st.markdown("### Question Palette")
        st.caption("Click any number to jump directly:")

        with st.container(key="mcq_palette_container"):
            # Palette Grid: 5 columns
            cols = st.columns(5)
            for i in range(total_q):
                q_item = questions_raw[i]
                qid = q_item["question_id"]
                is_ans = bool(qid in answers_dict and answers_dict[qid])
                is_m = bool(qid in marked_set)
                is_curr = (i == current_idx)

                num_str = f"[{i+1}]" if is_curr else f"{i+1}"

                # Question Palette Color Coding:
                # 🔵 Blue: In Review
                # 🟢 Green: Attended
                # 🔴 Red: Not Attended
                if is_m:
                    icon = "🚩✓" if is_ans else "🚩"
                    label = f":blue[**{num_str}** {icon}]"
                    help_text = f"Question {i+1}: In Review{' (Answered)' if is_ans else ' (Unanswered)'}{' • Active' if is_curr else ''}"
                elif is_ans:
                    label = f":green[**{num_str}** ✓]"
                    help_text = f"Question {i+1}: Attended • Answer: {answers_dict[qid]}{' • Active' if is_curr else ''}"
                else:
                    label = f":red[**{num_str}**]"
                    help_text = f"Question {i+1}: Not Attended{' • Active' if is_curr else ''}"

                col_target = cols[i % 5]
                if col_target.button(label, key=f"pal_btn_{i}", type="secondary", use_container_width=True, help=help_text):
                    st.session_state["current_question_idx"] = i
                    st.rerun()

        # Clean, explicit Legend Card
        st.markdown(
            f"""
            <div style="background: rgba(15, 23, 42, 0.6); border: 1px solid rgba(255,255,255,0.08); border-radius: 10px; padding: 12px 14px; margin-top: 14px;">
                <div style="font-size: 0.8rem; font-weight: 700; color: #f8fafc; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 8px;">
                    Question Status
                </div>
                <div style="display: flex; flex-direction: column; gap: 7px; font-size: 0.82rem;">
                    <div style="display: flex; align-items: center; justify-content: space-between;">
                        <span style="display: flex; align-items: center; gap: 8px; color: #86efac; font-weight: 600;">
                            <span style="display: inline-block; width: 10px; height: 10px; border-radius: 50%; background: #22c55e;"></span>
                            Attended (Green)
                        </span>
                        <span style="color: #86efac; font-weight: 700;">{att_count}</span>
                    </div>
                    <div style="display: flex; align-items: center; justify-content: space-between;">
                        <span style="display: flex; align-items: center; gap: 8px; color: #fca5a5; font-weight: 600;">
                            <span style="display: inline-block; width: 10px; height: 10px; border-radius: 50%; background: #ef4444;"></span>
                            Not Attended (Red)
                        </span>
                        <span style="color: #fca5a5; font-weight: 700;">{unatt_count}</span>
                    </div>
                    <div style="display: flex; align-items: center; justify-content: space-between;">
                        <span style="display: flex; align-items: center; gap: 8px; color: #93c5fd; font-weight: 600;">
                            <span style="display: inline-block; width: 10px; height: 10px; border-radius: 50%; background: #3b82f6;"></span>
                            In Review (Blue)
                        </span>
                        <span style="color: #93c5fd; font-weight: 700;">{rev_count}</span>
                    </div>
                    <div style="border-top: 1px solid rgba(255,255,255,0.08); margin-top: 4px; padding-top: 6px; color: #94a3b8; font-size: 0.76rem;">
                        Current Question indicated by <b>[ N ]</b>
                    </div>
                </div>
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

        with st.spinner("Scoring assessment and preparing personalized learning feedback..."):
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
