"""Create Quiz view allowing PDF upload, document inspection, and generation parameters."""
import streamlit as st
from config.settings import settings
from models.schemas import DifficultyLevel, QuizConfig
from repositories.quiz_repository import QuizRepository
from services.pdf_service import ExtractedDocument, PDFService
from services.question_generator import QuestionGeneratorService
from ui.components import render_hero_banner


def render_create_quiz_page(
    quiz_repo: QuizRepository,
    pdf_service: PDFService,
    question_service: QuestionGeneratorService,
):
    """Render the PDF upload and quiz generation screen."""
    render_hero_banner(
        title="Create a New Quiz",
        subtitle="Upload your study materials, configure difficulty tiers, and generate custom multiple-choice assessments.",
        badge="DOCUMENT-GROUNDED GENERATION",
    )

    st.subheader("1. Upload Educational Document")
    st.write(
        f"Select a PDF document (e.g. textbook chapter, lecture notes, syllabus, research summary). "
        f"Maximum file size: **{settings.MAX_UPLOAD_SIZE_MB} MB**."
    )

    uploaded_file = st.file_uploader(
        "Choose a PDF file",
        type=["pdf"],
        help="Upload an unencrypted PDF containing readable text.",
        key="pdf_uploader_widget",
    )

    extracted_doc: ExtractedDocument = None

    if uploaded_file is not None:
        file_bytes = uploaded_file.getvalue()
        filename = uploaded_file.name

        with st.spinner("Analyzing and parsing PDF content..."):
            extracted_doc = pdf_service.process_pdf(file_bytes, filename)

        if extracted_doc.error:
            if extracted_doc.is_scanned:
                st.error(
                    f"⚠️ **Scanned Document Detected:** {extracted_doc.error}\n\n"
                    "The uploaded PDF contains bitmap images of pages rather than selectable digital text. "
                    "Please upload a text-based PDF (such as a document exported directly from Word, LaTeX, Google Docs, or a digital textbook)."
                )
            else:
                st.error(f"❌ **Validation Error:** {extracted_doc.error}")
            return

        # Display Document Metadata Cards
        st.success(f"✅ Successfully validated **{extracted_doc.filename}**")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            size_kb = extracted_doc.file_size_bytes / 1024
            st.metric("File Size", f"{size_kb:.1f} KB" if size_kb < 1024 else f"{size_kb/1024:.2f} MB")
        with c2:
            st.metric("Page Count", f"{extracted_doc.page_count} pages")
        with c3:
            st.metric("Word Count", f"{extracted_doc.word_count:,} words")
        with c4:
            st.metric("Character Count", f"{extracted_doc.char_count:,} chars")

        # Text Preview Expander
        with st.expander("🔍 View Extracted Text Preview", expanded=False):
            st.text_area(
                "Document Text Excerpt",
                extracted_doc.extracted_text_preview,
                height=220,
                disabled=True,
            )

        st.divider()

        # Quiz Configuration Form
        st.subheader("2. Quiz Configuration")
        col_cfg1, col_cfg2 = st.columns(2)

        with col_cfg1:
            # Question Count Selector (Default 50, with 10, 20, 30, 50 options)
            question_count_choice = st.select_slider(
                "Number of Questions",
                options=[10, 20, 30, 50],
                value=settings.DEFAULT_QUESTION_COUNT,
                help="Select how many questions to generate from the document text.",
            )

            # Difficulty Level
            difficulty_choice = st.radio(
                "Difficulty Level",
                options=["Easy", "Medium", "Hard", "Mixed"],
                index=1,
                horizontal=True,
                help=(
                    "Easy: Definitions & direct facts.\n"
                    "Medium: Conceptual understanding & comparisons.\n"
                    "Hard: Multi-step reasoning & application.\n"
                    "Mixed: Balanced combination across all tiers."
                ),
            )

        with col_cfg2:
            topic_focus = st.text_input(
                "Topic or Concept Focus (Optional)",
                placeholder="e.g. Chapter 3, Photosynthesis, Thermodynamics, Sorting Algorithms",
                help="Focus question generation on a specific topic or chapter if present in the document.",
            )

            language = st.selectbox(
                "Language",
                options=["English", "Spanish", "French", "German", "Hindi"],
                index=0,
                help="Generate questions and explanations in the selected language.",
            )

            # Optional Quiz Timer
            timer_option = st.selectbox(
                "Quiz Timer (Optional)",
                options=["Untimed (No Limit)", "5 Minutes", "10 Minutes", "15 Minutes", "30 Minutes", "60 Minutes"],
                index=0,
                help="Set an optional countdown timer for practice under exam pressure.",
            )

        # Convert timer selection to minutes
        timer_minutes = None
        if "5 Minutes" in timer_option:
            timer_minutes = 5
        elif "10 Minutes" in timer_option:
            timer_minutes = 10
        elif "15 Minutes" in timer_option:
            timer_minutes = 15
        elif "30 Minutes" in timer_option:
            timer_minutes = 30
        elif "60 Minutes" in timer_option:
            timer_minutes = 60

        st.write("")

        # Confirmation & Generation Button
        col_btn1, col_btn2 = st.columns([2, 3])
        with col_btn1:
            generate_clicked = st.button(
                "⚡ Generate Assessment Now",
                type="primary",
                use_container_width=True,
            )

        if generate_clicked:
            # Persist document record
            doc_record = quiz_repo.save_document(
                filename=extracted_doc.filename,
                file_size_bytes=extracted_doc.file_size_bytes,
                page_count=extracted_doc.page_count,
                char_count=extracted_doc.char_count,
                extracted_text_preview=extracted_doc.extracted_text_preview,
                full_text=extracted_doc.full_text,
            )

            quiz_config = QuizConfig(
                document_id=doc_record.id,
                question_count=question_count_choice,
                difficulty=DifficultyLevel(difficulty_choice),
                topic_focus=topic_focus if topic_focus.strip() else None,
                language=language,
                time_limit_minutes=timer_minutes,
            )

            with st.status("Generating high-quality multiple choice questions...", expanded=True) as status:
                st.write("Chunking and distributing source context across document sections...")
                st.write(f"Querying AI model for {question_count_choice} {difficulty_choice} MCQs...")

                questions, warning_msg = question_service.generate_quiz_questions(
                    extracted_doc=extracted_doc,
                    config=quiz_config,
                )

                if not questions:
                    status.update(label="Generation Failed!", state="error", expanded=True)
                    st.error(warning_msg or "Failed to generate questions.")
                    return

                st.write(f"Validating schema, ensuring 4 distinct options and single correct answers...")
                status.update(label="Questions Generated Successfully!", state="complete", expanded=False)

            if warning_msg:
                st.warning(warning_msg)

            # Persist quiz
            quiz_record = quiz_repo.save_quiz(
                document_id=doc_record.id,
                difficulty=difficulty_choice,
                question_count=len(questions),
                questions=questions,
                topic_focus=topic_focus if topic_focus.strip() else None,
                language=language,
            )

            # Initialize Quiz Taking State in Session
            st.session_state["active_quiz"] = {
                "quiz_id": quiz_record.id,
                "document_name": extracted_doc.filename,
                "difficulty": difficulty_choice,
                "question_count": len(questions),
                "questions": [q.model_dump() for q in questions],
                "time_limit_minutes": timer_minutes,
            }
            st.session_state["quiz_answers"] = {}  # {question_id: selected_key}
            st.session_state["quiz_marked"] = set()  # set of question_ids marked for review
            st.session_state["current_question_idx"] = 0
            st.session_state["quiz_start_timestamp"] = None
            st.session_state["active_nav"] = "Take Quiz"
            st.rerun()

    else:
        st.info("👆 Please upload a PDF document above to unlock configuration and question generation.")
