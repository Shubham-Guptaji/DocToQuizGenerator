"""SQLAlchemy models and database session management for persistent local storage."""
import datetime
import json
import uuid
from typing import Generator
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from config.settings import settings

Base = declarative_base()


class DocumentModel(Base):
    """Uploaded PDF document metadata and extracted content."""
    __tablename__ = "documents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    filename = Column(String(255), nullable=False)
    file_size_bytes = Column(Integer, nullable=False)
    page_count = Column(Integer, nullable=False)
    char_count = Column(Integer, nullable=False)
    extracted_text_preview = Column(Text, nullable=False)
    full_text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))

    # Relationships
    quizzes = relationship("QuizModel", back_populates="document", cascade="all, delete-orphan")


class QuizModel(Base):
    """Generated quiz configuration and question collection."""
    __tablename__ = "quizzes"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    difficulty = Column(String(20), nullable=False, default="Medium")
    question_count = Column(Integer, nullable=False, default=50)
    topic_focus = Column(String(100), nullable=True)
    language = Column(String(50), nullable=False, default="English")
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))

    # Relationships
    document = relationship("DocumentModel", back_populates="quizzes")
    questions = relationship("QuestionModel", back_populates="quiz", cascade="all, delete-orphan")
    attempts = relationship("QuizAttemptModel", back_populates="quiz", cascade="all, delete-orphan")


class QuestionModel(Base):
    """Individual Multiple Choice Question belonging to a Quiz."""
    __tablename__ = "questions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    quiz_id = Column(String(36), ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False)
    question_id_label = Column(String(20), nullable=False)  # e.g. "Q1"
    question_text = Column(Text, nullable=False)
    options_json = Column(Text, nullable=False)  # JSON serialized dict {"A": "...", "B": "..."}
    correct_answer = Column(String(5), nullable=False)  # "A", "B", "C", "D"
    explanation = Column(Text, nullable=False)
    topic = Column(String(100), nullable=False, default="General")
    difficulty = Column(String(20), nullable=False, default="Medium")
    source_reference = Column(String(255), nullable=True)

    # Relationships
    quiz = relationship("QuizModel", back_populates="questions")


class QuizAttemptModel(Base):
    """Record of a user's quiz attempt, scores, and generated feedback."""
    __tablename__ = "quiz_attempts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    quiz_id = Column(String(36), ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False)
    total_questions = Column(Integer, nullable=False)
    correct_count = Column(Integer, nullable=False)
    incorrect_count = Column(Integer, nullable=False)
    unanswered_count = Column(Integer, nullable=False)
    score_percentage = Column(Float, nullable=False)
    accuracy_rate = Column(Float, nullable=False)
    time_taken_seconds = Column(Integer, nullable=False, default=0)
    performance_grade = Column(String(10), nullable=False)
    ai_feedback_json = Column(Text, nullable=True)  # Serialized AIFeedback dict
    topic_breakdowns_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))

    # Relationships
    quiz = relationship("QuizModel", back_populates="attempts")
    user_answers = relationship("UserAnswerModel", back_populates="attempt", cascade="all, delete-orphan")


class UserAnswerModel(Base):
    """Record of an individual question response in an attempt."""
    __tablename__ = "user_answers"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    attempt_id = Column(String(36), ForeignKey("quiz_attempts.id", ondelete="CASCADE"), nullable=False)
    question_id_label = Column(String(20), nullable=False)
    selected_answer = Column(String(5), nullable=True)  # "A", "B", "C", "D" or None
    is_correct = Column(Boolean, nullable=False, default=False)
    is_unanswered = Column(Boolean, nullable=False, default=True)

    # Relationships
    attempt = relationship("QuizAttemptModel", back_populates="user_answers")


# Database engine and session factory
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {},
    echo=False,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    """Create all database tables if they do not exist."""
    Base.metadata.create_all(bind=engine)


def get_db_session() -> Generator:
    """Provide a transactional database session context."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
