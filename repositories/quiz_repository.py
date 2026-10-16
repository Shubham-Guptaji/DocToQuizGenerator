"""Data access repository for documents, quizzes, attempts, and analytics."""
import json
from typing import Any, Dict, List, Optional
from sqlalchemy import desc, func
from sqlalchemy.orm import Session
from models.database import (
    DocumentModel,
    QuestionModel,
    QuizAttemptModel,
    QuizModel,
    SessionLocal,
    UserAnswerModel,
    init_db,
)
from models.schemas import (
    DocumentMetadata,
    QuestionItem,
    QuizResult,
    TopicPerformance,
)
from utils.logging_config import get_logger

logger = get_logger("quiz_repository")


class QuizRepository:
    """Encapsulates persistence and retrieval operations for the quiz system."""

    def __init__(self, session_factory=SessionLocal):
        self.session_factory = session_factory
        # Ensure tables exist
        init_db()

    def get_session(self) -> Session:
        return self.session_factory()

    def save_document(
        self,
        filename: str,
        file_size_bytes: int,
        page_count: int,
        char_count: int,
        extracted_text_preview: str,
        full_text: str,
    ) -> DocumentModel:
        """Persist document metadata and text."""
        with self.get_session() as db:
            doc = DocumentModel(
                filename=filename,
                file_size_bytes=file_size_bytes,
                page_count=page_count,
                char_count=char_count,
                extracted_text_preview=extracted_text_preview,
                full_text=full_text,
            )
            db.add(doc)
            db.commit()
            db.refresh(doc)
            logger.info(f"Saved document '{filename}' with ID {doc.id}")
            return doc

    def get_document(self, document_id: str) -> Optional[DocumentModel]:
        """Retrieve document by ID."""
        with self.get_session() as db:
            return db.query(DocumentModel).filter(DocumentModel.id == document_id).first()

    def save_quiz(
        self,
        document_id: str,
        difficulty: str,
        question_count: int,
        questions: List[QuestionItem],
        topic_focus: Optional[str] = None,
        language: str = "English",
    ) -> QuizModel:
        """Persist a generated quiz and its questions."""
        with self.get_session() as db:
            quiz = QuizModel(
                document_id=document_id,
                difficulty=difficulty,
                question_count=question_count,
                topic_focus=topic_focus,
                language=language,
            )
            db.add(quiz)
            db.flush()  # Generate quiz.id

            for q in questions:
                opts_data = q.options.model_dump() if hasattr(q.options, "model_dump") else q.options
                q_model = QuestionModel(
                    quiz_id=quiz.id,
                    question_id_label=q.question_id,
                    question_text=q.question,
                    options_json=json.dumps(opts_data),
                    correct_answer=q.correct_answer,
                    explanation=q.explanation,
                    topic=q.topic,
                    difficulty=q.difficulty,
                    source_reference=q.source_reference,
                )
                db.add(q_model)

            db.commit()
            db.refresh(quiz)
            logger.info(f"Saved quiz {quiz.id} with {len(questions)} questions")
            return quiz

    def get_quiz_with_questions(self, quiz_id: str) -> Optional[Dict[str, Any]]:
        """Fetch quiz details and reconstructed QuestionItem list."""
        with self.get_session() as db:
            quiz = db.query(QuizModel).filter(QuizModel.id == quiz_id).first()
            if not quiz:
                return None

            questions_data: List[QuestionItem] = []
            for q in quiz.questions:
                options = json.loads(q.options_json)
                questions_data.append(
                    QuestionItem(
                        question_id=q.question_id_label,
                        question=q.question_text,
                        options=options,
                        correct_answer=q.correct_answer,
                        explanation=q.explanation,
                        topic=q.topic,
                        difficulty=q.difficulty,
                        source_reference=q.source_reference,
                    )
                )

            return {
                "id": quiz.id,
                "document_id": quiz.document_id,
                "document_name": quiz.document.filename if quiz.document else "Unknown Document",
                "difficulty": quiz.difficulty,
                "question_count": quiz.question_count,
                "topic_focus": quiz.topic_focus,
                "language": quiz.language,
                "created_at": quiz.created_at,
                "questions": questions_data,
            }

    def get_available_quizzes(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Fetch list of generated quizzes available to attempt."""
        with self.get_session() as db:
            quizzes = (
                db.query(QuizModel)
                .order_by(desc(QuizModel.created_at))
                .limit(limit)
                .all()
            )
            return [
                {
                    "quiz_id": q.id,
                    "document_name": q.document.filename if q.document else "Unknown Document",
                    "difficulty": q.difficulty,
                    "question_count": q.question_count,
                    "created_at": q.created_at,
                }
                for q in quizzes
            ]

    def save_quiz_attempt(
        self,
        quiz_id: str,
        result: QuizResult,
        ai_feedback_dict: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Persist a completed quiz attempt, user answers, and AI feedback."""
        with self.get_session() as db:
            attempt = QuizAttemptModel(
                quiz_id=quiz_id,
                total_questions=result.total_questions,
                correct_count=result.correct_count,
                incorrect_count=result.incorrect_count,
                unanswered_count=result.unanswered_count,
                score_percentage=result.score_percentage,
                accuracy_rate=result.accuracy_rate,
                time_taken_seconds=result.time_taken_seconds,
                performance_grade=result.performance_grade,
                ai_feedback_json=json.dumps(ai_feedback_dict) if ai_feedback_dict else None,
                topic_breakdowns_json=json.dumps([t.model_dump() for t in result.topic_breakdowns]),
            )
            db.add(attempt)
            db.flush()

            for rev in result.reviews:
                ans = UserAnswerModel(
                    attempt_id=attempt.id,
                    question_id_label=rev.question_id,
                    selected_answer=rev.selected_answer,
                    is_correct=rev.is_correct,
                    is_unanswered=rev.is_unanswered,
                )
                db.add(ans)

            db.commit()
            logger.info(f"Saved quiz attempt {attempt.id} for quiz {quiz_id}")
            return attempt.id

    def update_attempt_feedback(self, attempt_id: str, ai_feedback_dict: Dict[str, Any]) -> None:
        """Update an attempt with asynchronously or lazily generated AI feedback."""
        with self.get_session() as db:
            attempt = db.query(QuizAttemptModel).filter(QuizAttemptModel.id == attempt_id).first()
            if attempt:
                attempt.ai_feedback_json = json.dumps(ai_feedback_dict)
                db.commit()
                logger.info(f"Updated feedback for attempt {attempt_id}")

    def get_attempt(self, attempt_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve attempt details, questions, answers, and feedback."""
        with self.get_session() as db:
            attempt = db.query(QuizAttemptModel).filter(QuizAttemptModel.id == attempt_id).first()
            if not attempt:
                return None

            quiz = attempt.quiz
            doc_name = quiz.document.filename if quiz and quiz.document else "Unknown Document"

            # Map user answers
            user_answers_map = {
                ans.question_id_label: {
                    "selected": ans.selected_answer,
                    "is_correct": ans.is_correct,
                    "is_unanswered": ans.is_unanswered,
                }
                for ans in attempt.user_answers
            }

            # Map questions
            questions_list = []
            if quiz:
                for q in quiz.questions:
                    ans_info = user_answers_map.get(
                        q.question_id_label,
                        {"selected": None, "is_correct": False, "is_unanswered": True},
                    )
                    questions_list.append({
                        "question_id": q.question_id_label,
                        "question": q.question_text,
                        "options": json.loads(q.options_json),
                        "correct_answer": q.correct_answer,
                        "explanation": q.explanation,
                        "topic": q.topic,
                        "difficulty": q.difficulty,
                        "source_reference": q.source_reference,
                        "selected_answer": ans_info["selected"],
                        "is_correct": ans_info["is_correct"],
                        "is_unanswered": ans_info["is_unanswered"],
                    })

            feedback_data = json.loads(attempt.ai_feedback_json) if attempt.ai_feedback_json else None
            topic_data = json.loads(attempt.topic_breakdowns_json) if attempt.topic_breakdowns_json else []

            return {
                "attempt_id": attempt.id,
                "quiz_id": attempt.quiz_id,
                "document_name": doc_name,
                "difficulty": quiz.difficulty if quiz else "Medium",
                "total_questions": attempt.total_questions,
                "correct_count": attempt.correct_count,
                "incorrect_count": attempt.incorrect_count,
                "unanswered_count": attempt.unanswered_count,
                "score_percentage": attempt.score_percentage,
                "accuracy_rate": attempt.accuracy_rate,
                "time_taken_seconds": attempt.time_taken_seconds,
                "performance_grade": attempt.performance_grade,
                "ai_feedback": feedback_data,
                "topic_breakdowns": topic_data,
                "completed_at": attempt.created_at,
                "questions": questions_list,
            }

    def get_all_attempts(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Fetch list of past attempts ordered by completion date descending."""
        with self.get_session() as db:
            attempts = (
                db.query(QuizAttemptModel)
                .order_by(desc(QuizAttemptModel.created_at))
                .limit(limit)
                .all()
            )

            results = []
            for att in attempts:
                quiz = att.quiz
                doc_name = quiz.document.filename if quiz and quiz.document else "Unknown Document"
                results.append({
                    "attempt_id": att.id,
                    "quiz_id": att.quiz_id,
                    "document_name": doc_name,
                    "difficulty": quiz.difficulty if quiz else "Medium",
                    "total_questions": att.total_questions,
                    "correct_count": att.correct_count,
                    "score_percentage": att.score_percentage,
                    "time_taken_seconds": att.time_taken_seconds,
                    "performance_grade": att.performance_grade,
                    "completed_at": att.created_at,
                })
            return results

    def get_dashboard_stats(self) -> Dict[str, Any]:
        """Aggregate statistical metrics for home dashboard."""
        with self.get_session() as db:
            total_attempts = db.query(func.count(QuizAttemptModel.id)).scalar() or 0
            if total_attempts == 0:
                return {
                    "total_quizzes": 0,
                    "average_score": 0.0,
                    "best_score": 0.0,
                    "recent_attempts": [],
                }

            avg_score = db.query(func.avg(QuizAttemptModel.score_percentage)).scalar() or 0.0
            best_score = db.query(func.max(QuizAttemptModel.score_percentage)).scalar() or 0.0

            recent = self.get_all_attempts(limit=5)

            return {
                "total_quizzes": total_attempts,
                "average_score": round(float(avg_score), 1),
                "best_score": round(float(best_score), 1),
                "recent_attempts": recent,
            }

    def delete_attempt(self, attempt_id: str) -> bool:
        """Delete an attempt by ID."""
        with self.get_session() as db:
            attempt = db.query(QuizAttemptModel).filter(QuizAttemptModel.id == attempt_id).first()
            if attempt:
                db.delete(attempt)
                db.commit()
                logger.info(f"Deleted attempt {attempt_id}")
                return True
            return False

    def clear_all_history(self) -> None:
        """Delete all recorded attempts and quizzes for a clean state."""
        with self.get_session() as db:
            db.query(UserAnswerModel).delete()
            db.query(QuizAttemptModel).delete()
            db.query(QuestionModel).delete()
            db.query(QuizModel).delete()
            db.query(DocumentModel).delete()
            db.commit()
            logger.info("Cleared all quiz history and documents.")
