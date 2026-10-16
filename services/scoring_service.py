"""Deterministic Python scoring engine and answer review generation."""
from collections import defaultdict
from typing import Dict, List, Optional
from models.schemas import (
    QuestionItem,
    QuestionReviewItem,
    QuizResult,
    QuizSubmission,
    TopicPerformance,
)
from utils.logging_config import get_logger

logger = get_logger("scoring_service")


class ScoringService:
    """Computes exact, deterministic quiz results, topic breakdowns, and review items."""

    @staticmethod
    def format_time(seconds: int) -> str:
        """Format elapsed seconds into readable 'Xm Ys' or 'Xs' format."""
        if seconds < 0:
            return "0s"
        minutes = seconds // 60
        remaining_sec = seconds % 60
        if minutes > 0:
            return f"{minutes}m {remaining_sec}s"
        return f"{remaining_sec}s"

    @staticmethod
    def calculate_grade(percentage: float) -> str:
        """Assign letter grade based on score percentage."""
        if percentage >= 90.0:
            return "A+"
        elif percentage >= 80.0:
            return "A"
        elif percentage >= 70.0:
            return "B"
        elif percentage >= 60.0:
            return "C"
        elif percentage >= 50.0:
            return "D"
        else:
            return "F"

    @staticmethod
    def get_summary_message(percentage: float, correct: int, total: int) -> str:
        """Generate encouraging, performance-grounded summary statement."""
        if percentage >= 90.0:
            return f"Outstanding mastery! You scored {correct}/{total} ({percentage:.1f}%). Excellent comprehension."
        elif percentage >= 75.0:
            return f"Great job! You scored {correct}/{total} ({percentage:.1f}%). Strong foundation across most concepts."
        elif percentage >= 50.0:
            return f"Fair performance. You scored {correct}/{total} ({percentage:.1f}%). Review the key topics to reinforce retention."
        else:
            return f"Needs review. You scored {correct}/{total} ({percentage:.1f}%). Take time to study the explanations and revision plan below."

    def score_quiz(
        self,
        questions: List[QuestionItem],
        submission: QuizSubmission,
    ) -> QuizResult:
        """
        Evaluate user answers against correct keys using pure Python logic.
        Policy: +1 point per correct answer, 0 for incorrect, 0 for unanswered.
        """
        user_answers = submission.answers
        total_questions = len(questions)
        correct_count = 0
        incorrect_count = 0
        unanswered_count = 0

        # Topic tracking: topic -> {"total": int, "correct": int}
        topic_stats: Dict[str, Dict[str, int]] = defaultdict(lambda: {"total": 0, "correct": 0})

        reviews: List[QuestionReviewItem] = []

        for q in questions:
            q_id = q.question_id
            user_choice = user_answers.get(q_id)
            if user_choice:
                user_choice = str(user_choice).strip().upper()

            correct_key = q.correct_answer.strip().upper()
            topic = q.topic or "General"
            topic_stats[topic]["total"] += 1

            if not user_choice:
                # Unanswered
                unanswered_count += 1
                is_correct = False
                is_unanswered = True
                mistake_analysis = "This question was left unanswered."
            elif user_choice == correct_key:
                # Correct
                correct_count += 1
                topic_stats[topic]["correct"] += 1
                is_correct = True
                is_unanswered = False
                mistake_analysis = None
            else:
                # Incorrect
                incorrect_count += 1
                is_correct = False
                is_unanswered = False
                user_option_text = q.options.get(user_choice, "")
                correct_option_text = q.options.get(correct_key, "")
                mistake_analysis = (
                    f"You selected ({user_choice}): '{user_option_text}'. "
                    f"The correct answer is ({correct_key}): '{correct_option_text}'."
                )

            reviews.append(
                QuestionReviewItem(
                    question_id=q.question_id,
                    question=q.question,
                    options=q.options,
                    selected_answer=user_choice if not is_unanswered else None,
                    correct_answer=correct_key,
                    is_correct=is_correct,
                    is_unanswered=is_unanswered,
                    explanation=q.explanation,
                    mistake_analysis=mistake_analysis,
                    topic=topic,
                    difficulty=q.difficulty,
                    source_reference=q.source_reference,
                )
            )

        # Calculate scores
        score_percentage = round((correct_count / total_questions) * 100.0, 1) if total_questions > 0 else 0.0

        attempted_count = total_questions - unanswered_count
        accuracy_rate = round((correct_count / attempted_count) * 100.0, 1) if attempted_count > 0 else 0.0

        grade = self.calculate_grade(score_percentage)
        summary = self.get_summary_message(score_percentage, correct_count, total_questions)
        formatted_time = self.format_time(submission.time_taken_seconds)

        # Assemble topic breakdowns
        topic_breakdowns: List[TopicPerformance] = []
        for t_name, stats in topic_stats.items():
            t_total = stats["total"]
            t_correct = stats["correct"]
            t_pct = round((t_correct / t_total) * 100.0, 1) if t_total > 0 else 0.0
            topic_breakdowns.append(
                TopicPerformance(
                    topic=t_name,
                    total_questions=t_total,
                    correct_count=t_correct,
                    accuracy_percentage=t_pct,
                )
            )
        # Sort topics alphabetically
        topic_breakdowns.sort(key=lambda x: x.topic)

        logger.info(
            f"Quiz {submission.quiz_id} scored: {correct_count}/{total_questions} "
            f"({score_percentage}%), Time: {formatted_time}"
        )

        return QuizResult(
            quiz_id=submission.quiz_id,
            total_questions=total_questions,
            correct_count=correct_count,
            incorrect_count=incorrect_count,
            unanswered_count=unanswered_count,
            score_percentage=score_percentage,
            accuracy_rate=accuracy_rate,
            time_taken_seconds=submission.time_taken_seconds,
            time_taken_formatted=formatted_time,
            performance_grade=grade,
            summary_message=summary,
            topic_breakdowns=topic_breakdowns,
            reviews=reviews,
        )
