# AI-Powered MCQ Generator and Smart Quiz Platform 🎓

A modern, production-grade Python web application that transforms educational PDF documents into rigorous multiple-choice assessments (MCQs) using the official **Google Gen AI Python SDK** with deterministic Python scoring, detailed question-by-question mistake analysis, and personalized AI learning roadmaps.

---

## 🌟 Key Features

- **Document-Grounded MCQ Generation**: Questions are extracted strictly from the uploaded PDF text using Google Gemini (`gemini-3.8-flash` / `gemini-3.5-flash-lite`), eliminating unsupported external trivia or hallucinations.
- **Robust Multi-Engine PDF Processing**: Dual-engine extraction utilizing pure-Python `pypdf` with optional `PyMuPDF` acceleration. Includes automated detection for password protection, corrupted PDFs, and scanned image documents (with OCR guidance).
- **Customizable Assessment Config**: Select from **10, 20, 30, or 50 questions** across **Easy**, **Medium**, **Hard**, or **Mixed** difficulty tiers, with optional topic filters and language selection.
- **Interactive Exam Interface**: Single-question focus view, 5-column Jump-to-Question Palette, Answered/Unanswered tracker, completion progress bar, "Mark for Review" flags, and an optional countdown timer.
- **Deterministic Python Scoring**: Exact, tamper-proof Python scoring logic (1 point per correct answer, 0 for wrong/unanswered). Calculates total score percentage, accuracy rate, time taken, letter grade (A+ through F), and topic-level mastery percentages.
- **Detailed Question Review**: Color-coded review cards with filters (*All Questions*, *Correct*, *Incorrect*, *Unanswered*), displaying the correct option, your selected option, full pedagogical explanation, mistake analysis, and source page citations.
- **🔁 Targeted Missed-Questions Retry**: One-click generation of a targeted revision quiz featuring only the questions you missed or left unanswered.
- **Actionable AI Feedback & Study Roadmap**: Analyzes your actual error patterns to deliver overall assessment, strongest topics, weak concepts requiring review, prioritized step-by-step revision checklist, and suggested follow-up study activities.
- **Persistent Local History**: Full SQLite persistence with SQLAlchemy ORM. Track score progression over time via interactive **Plotly** charts, review historical attempts, or delete records.
- **Dual Interface (UI + REST API)**: Runs seamlessly as a rich **Streamlit** dashboard or as a high-performance **FastAPI** backend exposing documented OpenAPI REST endpoints (`/api/upload-pdf`, `/api/generate-quiz`, `/api/submit-quiz`, `/api/history`).
- **Offline Mock Provider Mode**: Fully functional offline fallback mode allowing complete quiz generation, taking, scoring, and testing even without an external API key or network access.

---

## 🏛️ Architecture & Project Structure

The project follows a clean separation of concerns:

```
ai-quiz-platform/
│
├── app.py                      # Main Streamlit dashboard application
├── api.py                      # Optional FastAPI REST backend
├── requirements.txt            # Frozen, tested dependencies
├── .env.example                # Environment variable configuration template
├── .gitignore                  # Git ignore rules for Python, SQLite, temp files
├── README.md                   # Complete architectural guide & documentation
│
├── config/                     # Configuration management
│   ├── __init__.py
│   └── settings.py             # Settings loader from .env with type annotations
│
├── models/                     # Data schemas and database ORM
│   ├── __init__.py
│   ├── database.py             # SQLAlchemy models (Document, Quiz, Question, Attempt, UserAnswer)
│   └── schemas.py              # Pydantic V2 models for validation, serialization, and AI schemas
│
├── repositories/               # Data access layer
│   ├── __init__.py
│   └── quiz_repository.py      # CRUD operations, history management, and dashboard analytics
│
├── services/                   # Business logic layer
│   ├── __init__.py
│   ├── pdf_service.py          # PDF text extraction, scanned PDF detection, and chunking
│   ├── ai_provider.py          # Gemini SDK integration and MockAIProvider fallback
│   ├── question_generator.py   # MCQ generation orchestrator and quality validator
│   ├── scoring_service.py      # Deterministic Python scoring engine
│   └── feedback_service.py     # AI educational feedback and rule-based diagnostic fallback
│
├── ui/                         # Streamlit UI modules and views
│   ├── __init__.py
│   ├── components.py           # Custom CSS, hero banners, metric cards, and badge components
│   ├── dashboard.py            # Home dashboard with progress charts and recent activity
│   ├── create_quiz.py          # PDF upload, document metadata inspection, and quiz configuration
│   ├── take_quiz.py            # Interactive quiz taking, question palette, and submission
│   ├── results.py              # Detailed results review, Plotly analytics, and retry flow
│   └── history.py              # Historical attempt browser, filters, and deletion controls
│
├── utils/                      # Utilities and security safeguards
│   ├── __init__.py
│   ├── validators.py           # File validation, prompt-injection sanitization, option sanity
│   └── logging_config.py       # Structured logging with automatic secret masking
│
├── sample_docs/                # Verified test fixtures
│   └── machine_learning_primer.pdf  # 3-page sample educational PDF document
│
├── scripts/                    # Automation scripts
│   └── generate_sample_pdf.py  # Standalone script to synthesize sample educational PDFs
│
└── tests/                      # Automated test suite (24 tests)
    ├── __init__.py
    ├── test_pdf_processing.py
    ├── test_question_validation.py
    ├── test_scoring.py
    ├── test_feedback.py
    ├── test_database.py
    ├── test_ai_provider.py
    └── test_api.py
```

---

## 🚀 Quickstart & Installation

### 1. Prerequisites
- Python 3.10 to 3.14+ installed on your system.

### 2. Clone and Setup Environment
Navigate to the project root directory and create a virtual environment:

```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows (PowerShell):
.\.venv\Scripts\Activate.ps1
# Windows (Command Prompt):
.\.venv\Scripts\activate.bat
# Linux / macOS:
source .venv/bin/activate
```

### 3. Install Dependencies
Install all required libraries:

```bash
pip install -r requirements.txt
```

### 4. Configure Gemini API Key (Optional but Recommended)
Copy the template configuration file:

```bash
cp .env.example .env
```

Edit `.env` and paste your Google Gemini API key:
```ini
GEMINI_API_KEY=your_actual_gemini_api_key_here
GEMINI_MODEL=gemini-3.8-flash
```
> **Note:** If no API key is provided, the platform automatically activates **Local Mock Provider Mode**, generating realistic educational assessments completely offline for testing and demonstration. You can also configure your API key at any time directly through the in-app **⚙️ Settings** screen.

---

## 🖥️ Running the Application

### Option A: Interactive Streamlit Web Dashboard (Recommended)
Launch the web interface:

```bash
streamlit run app.py
```
Open your browser and navigate to: **`http://localhost:8501`**

### Option B: FastAPI REST API
Launch the REST backend with Swagger OpenAPI documentation:

```bash
uvicorn api:app --reload --port 8000
```
- Interactive API Documentation (Swagger UI): **`http://localhost:8000/docs`**
- Alternative Documentation (ReDoc): **`http://localhost:8000/redoc`**

---

## 🧪 Running Automated Tests

The platform includes 24 automated unit and integration tests covering PDF parsing, question validation, deterministic scoring, AI fallbacks, SQLAlchemy persistence, and FastAPI endpoints:

```bash
# Run full test suite
pytest -v

# Run with coverage report
pytest --cov=. -v
```

---

## 🔒 Security, Privacy & Reliability Safeguards

1. **Prompt Injection Defense**: All extracted document text passes through `sanitize_prompt_injection()`, which neutralizes override directives (such as *"ignore prior instructions"*) before text is sent to the AI model.
2. **Secret Redaction**: Structured logging in `utils/logging_config.py` automatically filters and redacts API keys and bearer tokens from logs.
3. **No General Knowledge Hallucinations**: System instructions strictly constrain the model to facts and concepts present in the uploaded document.
4. **Deterministic Scoring**: Answers are evaluated entirely in Python (`scoring_service.py`), ensuring that scoring is never delegated to the AI model.
5. **No Answer Leakage**: Correct answer keys and explanations are never exposed in the quiz-taking interface before submission.

---

## 📖 How to Obtain a Google Gemini API Key

1. Visit [Google AI Studio](https://aistudio.google.com/).
2. Sign in with your Google account.
3. Click on **"Get API key"** and create a key in a new or existing Google Cloud project.
4. Copy the API key and paste it into `.env` or input it directly in the in-app **⚙️ Settings** page.
