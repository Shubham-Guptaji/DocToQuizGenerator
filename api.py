"""FastAPI REST API application exposing backend endpoints for the Quiz Platform."""
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, File, HTTPException, Query, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from config.settings import settings
from models.schemas import (
    AIFeedback,
    DifficultyLevel,
    DocumentMetadata,
    QuestionItem,
    QuizConfig,
    QuizResult,
    QuizSubmission,
)
from repositories.quiz_repository import QuizRepository
from services.feedback_service import FeedbackService
from services.pdf_service import PDFService
from services.question_generator import QuestionGeneratorService
from services.scoring_service import ScoringService
from utils.logging_config import get_logger

logger = get_logger("api")

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="REST API for AI-Powered PDF MCQ Generator and Smart Quiz Platform",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Service singletons
pdf_service = PDFService()
quiz_repo = QuizRepository()
question_service = QuestionGeneratorService()
scoring_service = ScoringService()
feedback_service = FeedbackService()


@app.get("/api/health", tags=["System"])
def health_check():
    """Health check and AI provider status."""
    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "version": settings.VERSION,
        "gemini_api_key_configured": settings.has_gemini_api_key,
        "active_model": settings.GEMINI_MODEL,
    }


@app.post("/api/upload-pdf", response_model=DocumentMetadata, tags=["PDF Processing"])
async def upload_pdf(file: UploadFile = File(...)):
    """Upload and validate an educational PDF document."""
    contents = await file.read()
    extracted = pdf_service.process_pdf(contents, file.filename or "uploaded.pdf")

    if extracted.error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=extracted.error,
        )

    # Persist document metadata
    doc_record = quiz_repo.save_document(
        filename=extracted.filename,
        file_size_bytes=extracted.file_size_bytes,
        page_count=extracted.page_count,
        char_count=extracted.char_count,
        extracted_text_preview=extracted.extracted_text_preview,
        full_text=extracted.full_text,
    )

    return DocumentMetadata(
        document_id=doc_record.id,
        filename=extracted.filename,
        file_size_bytes=extracted.file_size_bytes,
        page_count=extracted.page_count,
        char_count=extracted.char_count,
        word_count=extracted.word_count,
        extracted_text_preview=extracted.extracted_text_preview,
        is_scanned_ocr_needed=extracted.is_scanned,
        created_at=doc_record.created_at.isoformat() if doc_record.created_at else None,
    )


@app.post("/api/generate-quiz", tags=["Quiz Generation"])
def generate_quiz(config: QuizConfig):
    """Generate multiple-choice questions from an uploaded document."""
    if not config.document_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="document_id is required to generate a quiz.",
        )

    doc_record = quiz_repo.get_document(config.document_id)
    if not doc_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID '{config.document_id}' not found.",
        )

    from services.pdf_service import ExtractedDocument
    extracted_doc = ExtractedDocument(
        filename=doc_record.filename,
        file_size_bytes=doc_record.file_size_bytes,
        page_count=doc_record.page_count,
        char_count=doc_record.char_count,
        word_count=len(doc_record.full_text.split()),
        extracted_text_preview=doc_record.extracted_text_preview,
        full_text=doc_record.full_text,
    )

    questions, warning = question_service.generate_quiz_questions(extracted_doc, config)
    if not questions:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=warning or "Failed to generate questions from document.",
        )

    # Persist quiz
    saved_quiz = quiz_repo.save_quiz(
        document_id=doc_record.id,
        difficulty=config.difficulty.value,
        question_count=len(questions),
        questions=questions,
        topic_focus=config.topic_focus,
        language=config.language,
    )

    # Strip correct answers for taking the quiz safely
    sanitized_questions = []
    for q in questions:
        sanitized_questions.append({
            "question_id": q.question_id,
            "question": q.question,
            "options": q.options,
            "topic": q.topic,
            "difficulty": q.difficulty,
            "source_reference": q.source_reference,
        })

    return {
        "quiz_id": saved_quiz.id,
        "document_name": doc_record.filename,
        "question_count": len(questions),
        "difficulty": config.difficulty.value,
        "warning": warning,
        "questions": sanitized_questions,
    }


@app.post("/api/submit-quiz", response_model=QuizResult, tags=["Quiz Submission"])
def submit_quiz(submission: QuizSubmission):
    """Submit quiz answers, compute deterministic score, and persist results."""
    quiz_data = quiz_repo.get_quiz_with_questions(submission.quiz_id)
    if not quiz_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Quiz '{submission.quiz_id}' not found.",
        )

    questions = quiz_data["questions"]
    result = scoring_service.score_quiz(questions, submission)

    # Generate AI feedback
    feedback = feedback_service.generate_feedback(result)

    # Persist attempt
    attempt_id = quiz_repo.save_quiz_attempt(
        quiz_id=submission.quiz_id,
        result=result,
        ai_feedback_dict=feedback.model_dump(),
    )
    result.attempt_id = attempt_id

    return result


@app.get("/api/history", tags=["Quiz History"])
def get_quiz_history(limit: int = Query(default=50, ge=1, le=200)):
    """Retrieve history of past completed quiz attempts."""
    return quiz_repo.get_all_attempts(limit=limit)


@app.get("/api/history/{attempt_id}", tags=["Quiz History"])
def get_attempt_detail(attempt_id: str):
    """Retrieve detailed results, answers, and feedback for an attempt."""
    attempt = quiz_repo.get_attempt(attempt_id)
    if not attempt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Attempt '{attempt_id}' not found.",
        )
    return attempt


@app.delete("/api/history/{attempt_id}", tags=["Quiz History"])
def delete_attempt(attempt_id: str):
    """Delete a specific quiz attempt."""
    success = quiz_repo.delete_attempt(attempt_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Attempt '{attempt_id}' not found.",
        )
    return {"message": f"Attempt {attempt_id} deleted successfully."}
