"""Settings view for configuring Gemini API keys, models, and viewing system health."""
import os
import streamlit as st
from config.settings import settings
from repositories.quiz_repository import QuizRepository
from services.ai_provider import GeminiAIProvider, get_ai_provider
from ui.components import render_hero_banner


def render_settings_page(quiz_repo: QuizRepository):
    """Render application configuration and AI provider management."""
    render_hero_banner(
        title="Settings & System Configuration",
        subtitle="Manage your API credentials, model parameters, and local data persistence.",
        badge="CONFIGURATION",
    )

    st.subheader("1. API Status & Model Configuration")

    is_configured = settings.has_gemini_api_key
    if is_configured:
        st.success("✅ **API Key is Active and Configured**")
    else:
        st.info(
            "ℹ️ **No API Key Detected**: Currently operating in offline evaluation mode. "
            "Enter your Google Gemini API key below to enable live question generation."
        )

    # API Key Input
    with st.form("api_key_form"):
        st.write("Enter your Google Gemini API Key to enable live question generation:")
        new_api_key = st.text_input(
            "Gemini API Key",
            value=settings.GEMINI_API_KEY if settings.has_gemini_api_key else "",
            type="password",
            help="Get a free key from Google AI Studio: https://aistudio.google.com/",
        )

        model_choice = st.selectbox(
            "Gemini Model",
            options=["gemini-3.8-flash", "gemini-3.5-flash-lite"],
            index=0 if settings.GEMINI_MODEL == "gemini-3.8-flash" else 1,
            help="gemini-3.8-flash is the recommended default for fast, accurate reasoning and structured JSON output.",
        )

        col_save, col_test = st.columns([1, 1])
        with col_save:
            save_clicked = st.form_submit_button("💾 Save Settings", type="primary", use_container_width=True)

        if save_clicked:
            clean_key = new_api_key.strip()
            settings.GEMINI_API_KEY = clean_key
            settings.GEMINI_MODEL = model_choice
            os.environ["GEMINI_API_KEY"] = clean_key
            os.environ["GEMINI_MODEL"] = model_choice

            # Persist to .env file
            env_file = settings.BASE_DIR / ".env"
            with open(env_file, "w", encoding="utf-8") as f:
                f.write(f"GEMINI_API_KEY={clean_key}\n")
                f.write(f"GEMINI_MODEL={model_choice}\n")
                f.write(f"APP_NAME={settings.APP_NAME}\n")
                f.write(f"MAX_UPLOAD_SIZE_MB={settings.MAX_UPLOAD_SIZE_MB}\n")
                f.write(f"DEFAULT_QUESTION_COUNT={settings.DEFAULT_QUESTION_COUNT}\n")

            st.success("Settings saved successfully! Environment updated.")
            st.rerun()

    # Connection Test
    st.write("")
    st.markdown("#### Test Gemini API Connection")
    if st.button("🧪 Test API Key", disabled=not settings.has_gemini_api_key):
        with st.spinner("Connecting to Google Gemini API..."):
            try:
                test_provider = GeminiAIProvider(api_key=settings.GEMINI_API_KEY, model=settings.GEMINI_MODEL)
                res = test_provider.generate_text("Reply with the exact word: 'CONNECTED'")
                if "CONNECTED" in res.upper():
                    st.success(f"🎉 Connection verified successfully with model `{settings.GEMINI_MODEL}`!")
                else:
                    st.success(f"Response received from model: {res}")
            except Exception as e:
                st.error(f"❌ Connection test failed: {e}")

    st.divider()

    # System & Database Information
    st.subheader("2. Database & Storage")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"**Database Engine:** SQLite (SQLAlchemy ORM)")
        st.markdown(f"**Database Location:** `{settings.DATABASE_URL}`")
    with c2:
        st.markdown(f"**Temp Upload Directory:** `{settings.TEMP_DIR}`")
        st.markdown(f"**Max File Size:** {settings.MAX_UPLOAD_SIZE_MB} MB")

    st.divider()

    # Security & Privacy Disclosure
    st.subheader("3. Security & Privacy Safeguards")
    st.markdown(
        """
        - **Untrusted Source Material:** Uploaded PDF content is processed as untrusted reference data with sanitization filters against prompt injection.
        - **Data Privacy:** Your uploaded document text is sent securely to Google Gemini solely to synthesize multiple-choice assessment questions and feedback.
        - **Secret Protection:** API keys and credentials are stored strictly in local environment variables and never logged or exposed in client responses.
        - **Local Single-User Architecture:** Database records, attempts, and questions remain stored on your local machine.
        """
    )
