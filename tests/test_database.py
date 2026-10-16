"""Automated tests for SQLAlchemy database models, persistence, and CRUD repository."""
import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models.database import Base
from models.schemas import QuestionItem, QuizResult, TopicPerformance, QuestionReviewItem
from repositories.quiz_repository import QuizRepository


@pytest.fixture
def in_memory_repo():
    """Create a temporary in-memory SQLite repository for isolation."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return QuizRepository(session_factory=session_factory)


def test_document_and_quiz_persistence(in_memory_repo):
    """Test saving a document, creating a quiz with questions, and retrieving it."""
    # 1. Save Document
    doc = in_memory_repo.save_document(
        filename="lecture1.pdf",
        file_size_bytes=4096,
        page_count=5,
        char_count=1200,
        extracted_text_preview="Preview of lecture 1...",
        full_text="Full text content of lecture 1.",
    )
    assert doc.id is not None
    assert doc.filename == "lecture1.pdf"

    # 2. Save Quiz with QuestionItems
    questions = [
        QuestionItem(
            question_id="Q1",
            question="What is PCA?",
            options={"A": "Dimensionality reduction", "B": "Clustering", "C": "Regression", "D": "Tree"},
            correct_answer="A",
            explanation="PCA projects data along principal components.",
            topic="Unsupervised",
            difficulty="Medium",
        )
    ]

    quiz = in_memory_repo.save_quiz(
        document_id=doc.id,
        difficulty="Medium",
        question_count=1,
        questions=questions,
        topic_focus="Unsupervised",
    )
    assert quiz.id is not None

    # 3. Retrieve Quiz
    retrieved = in_memory_repo.get_quiz_with_questions(quiz.id)
    assert retrieved is not None
    assert retrieved["document_name"] == "lecture1.pdf"
    assert len(retrieved["questions"]) == 1
    assert retrieved["questions"][0].question == "What is PCA?"


def test_attempt_persistence_and_stats(in_memory_repo):
    """Test saving a quiz attempt, user answers, and querying dashboard statistics."""
    doc = in_memory_repo.save_document("test.pdf", 1024, 1, 500, "prev", "full")
    questions = [
        QuestionItem(
            question_id="Q1",
            question="Test question?",
            options={"A": "1", "B": "2", "C": "3", "D": "4"},
            correct_answer="B",
            explanation="B is right.",
        )
    ]
    quiz = in_memory_repo.save_quiz(doc.id, "Easy", 1, questions)

    result = QuizResult(
        quiz_id=quiz.id,
        total_questions=1,
        correct_count=1,
        incorrect_count=0,
        unanswered_count=0,
        score_percentage=100.0,
        accuracy_rate=100.0,
        time_taken_seconds=20,
        time_taken_formatted="20s",
        performance_grade="A+",
        summary_message="Great",
        topic_breakdowns=[TopicPerformance(topic="General", total_questions=1, correct_count=1, accuracy_percentage=100.0)],
        reviews=[
            QuestionReviewItem(
                question_id="Q1",
                question="Test question?",
                options={"A": "1", "B": "2", "C": "3", "D": "4"},
                selected_answer="B",
                correct_answer="B",
                is_correct=True,
                is_unanswered=False,
                explanation="B is right.",
                topic="General",
                difficulty="Easy",
            )
        ],
    )

    attempt_id = in_memory_repo.save_quiz_attempt(quiz.id, result, {"overall_assessment": "Excellent"})
    assert attempt_id is not None

    stats = in_memory_repo.get_dashboard_stats()
    assert stats["total_quizzes"] == 1
    assert stats["average_score"] == 100.0
    assert stats["best_score"] == 100.0
    assert len(stats["recent_attempts"]) == 1
