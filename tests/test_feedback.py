"""Automated tests for feedback generation, weak-topic identification, and roadmaps."""
import pytest
from models.schemas import QuestionReviewItem, QuizResult, TopicPerformance
from services.feedback_service import FeedbackService


@pytest.fixture
def sample_quiz_result():
    return QuizResult(
        quiz_id="quiz_abc",
        total_questions=10,
        correct_count=6,
        incorrect_count=3,
        unanswered_count=1,
        score_percentage=60.0,
        accuracy_rate=66.7,
        time_taken_seconds=300,
        time_taken_formatted="5m 0s",
        performance_grade="C",
        summary_message="Fair performance.",
        topic_breakdowns=[
            TopicPerformance(topic="Supervised Learning", total_questions=4, correct_count=4, accuracy_percentage=100.0),
            TopicPerformance(topic="Backpropagation", total_questions=3, correct_count=1, accuracy_percentage=33.3),
            TopicPerformance(topic="Regularization", total_questions=3, correct_count=1, accuracy_percentage=33.3),
        ],
        reviews=[
            QuestionReviewItem(
                question_id="Q1",
                question="What is backpropagation?",
                options={"A": "Chain rule", "B": "Heuristics", "C": "Search", "D": "Clustering"},
                selected_answer="B",
                correct_answer="A",
                is_correct=False,
                is_unanswered=False,
                explanation="Backpropagation uses chain rule.",
                topic="Backpropagation",
                difficulty="Hard",
            )
        ],
    )


def test_rule_based_fallback_feedback(sample_quiz_result):
    """Test deterministic rule-based feedback generator."""
    service = FeedbackService()
    feedback = service.generate_fallback_feedback(sample_quiz_result)

    assert feedback.overall_assessment is not None
    assert len(feedback.strongest_topics) > 0
    assert "Supervised Learning" in feedback.strongest_topics

    # Backpropagation or Regularization should be flagged as weak topics (<60% accuracy)
    assert any("Backpropagation" in t or "Regularization" in t for t in feedback.weak_topics)
    assert len(feedback.prioritized_revision_plan) >= 3
    assert len(feedback.suggested_follow_up_activities) >= 2
    assert feedback.encouragement is not None
