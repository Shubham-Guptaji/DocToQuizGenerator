"""Main Streamlit application entrypoint for AI MCQ Generator & Smart Quiz Platform."""
import streamlit as st
from config.settings import settings
from repositories.quiz_repository import QuizRepository
from services.feedback_service import FeedbackService
from services.pdf_service import PDFService
from services.question_generator import QuestionGeneratorService
from services.scoring_service import ScoringService
from ui.components import render_custom_css
from ui.create_quiz import render_create_quiz_page
from ui.dashboard import render_dashboard_page
from ui.history import render_history_page
from ui.results import render_results_page
from ui.take_quiz import render_take_quiz_page

# Set page configuration
st.set_page_config(
    page_title=settings.APP_NAME,
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Apply custom styles and theme tokens
render_custom_css()

# Initialize core services
@st.cache_resource
def get_services():
    repo = QuizRepository()
    pdf_svc = PDFService()
    question_svc = QuestionGeneratorService(pdf_service=pdf_svc)
    scoring_svc = ScoringService()
    feedback_svc = FeedbackService()
    return repo, pdf_svc, question_svc, scoring_svc, feedback_svc


quiz_repo, pdf_service, question_service, scoring_service, feedback_service = get_services()

# Session navigation state
if "active_nav" not in st.session_state:
    st.session_state["active_nav"] = "Home Dashboard"

# Sidebar Branding and Navigation
with st.sidebar:
    st.markdown("## 🎓 **SmartQuiz**")
    st.caption("Smart PDF Assessment & Exam Platform")

    # Active quiz alert in sidebar
    if st.session_state.get("active_quiz"):
        active_q = st.session_state["active_quiz"]
        st.info(f"⏳ **Active Quiz in Progress:**\n{active_q['document_name'][:20]}...")

    nav_options = [
        "Home Dashboard",
        "Create Quiz",
        "Take Quiz",
        "Results & Review",
        "Quiz History",
    ]

    selected_nav = st.radio(
        "Navigation",
        options=nav_options,
        index=nav_options.index(st.session_state["active_nav"]) if st.session_state["active_nav"] in nav_options else 0,
        label_visibility="collapsed",
    )

    if selected_nav != st.session_state["active_nav"]:
        st.session_state["active_nav"] = selected_nav
        st.rerun()

    st.divider()

    st.markdown(
        """
        <div style="font-size:0.8rem; color:#64748b; line-height:1.5;">
            <b>Tips for Best Results:</b><br>
            • Upload clean PDFs with digital text<br>
            • Select Medium or Hard for deep conceptual questions<br>
            • Review explanations to reinforce knowledge
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.caption("Version 1.0.0")

# Render Selected View
current_page = st.session_state["active_nav"]

if current_page == "Home Dashboard":
    render_dashboard_page(quiz_repo=quiz_repo)
elif current_page == "Create Quiz":
    render_create_quiz_page(
        quiz_repo=quiz_repo,
        pdf_service=pdf_service,
        question_service=question_service,
    )
elif current_page == "Take Quiz":
    render_take_quiz_page(
        quiz_repo=quiz_repo,
        scoring_service=scoring_service,
        feedback_service=feedback_service,
    )
elif current_page == "Results & Review":
    render_results_page(
        quiz_repo=quiz_repo,
        feedback_service=feedback_service,
    )
elif current_page == "Quiz History":
    render_history_page(quiz_repo=quiz_repo)
