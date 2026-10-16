"""Automated tests for deterministic Python scoring, grade assignment, and reviews."""
import pytest
from models.schemas import QuestionItem, QuizSubmission
from services.scoring_service import ScoringService


@pytest.fixture
def scoring_service():
    return ScoringService()


@pytest.fixture
def sample_questions():
    return [
        QuestionItem(
            question_id="Q1",
            question="What does ReLU compute?",
            options={"A": "max(0, x)", "B": "1/(1+e^-x)", "C": "tanh(x)", "D": "x^2"},
            correct_answer="A",
            explanation="ReLU is max(0, x).",
            topic="Activation Functions",
            difficulty="Easy",
        ),
        QuestionItem(
            question_id="Q2",
            question="Which method promotes weight sparsity?",
            options={"A": "L2", "B": "L1", "C": "Adam", "D": "SGD"},
            correct_answer="B",
            explanation="L1 adds absolute penalty.",
            topic="Regularization",
            difficulty="Medium",
        ),
        QuestionItem(
            question_id="Q3",
            question="What is backpropagation based on?",
            options={"A": "Chain rule", "B": "Bayes theorem", "C": "Central limit", "D": "Monte Carlo"},
            correct_answer="A",
            explanation="Calculates gradients using chain rule.",
            topic="Optimization",
            difficulty="Hard",
        ),
        QuestionItem(
            question_id="Q4",
            question="What is an unsupervised algorithm?",
            options={"A": "Linear Regression", "B": "Random Forest", "C": "K-Means", "D": "SVM"},
            correct_answer="C",
            explanation="K-Means is unsupervised.",
            topic="Clustering",
            difficulty="Easy",
        ),
    ]


def test_perfect_score(scoring_service, sample_questions):
    """Test 100% score calculation."""
    submission = QuizSubmission(
        quiz_id="test_quiz_1",
        time_taken_seconds=120,
        answers={"Q1": "A", "Q2": "B", "Q3": "A", "Q4": "C"},
    )
    res = scoring_service.score_quiz(sample_questions, submission)
    assert res.total_questions == 4
    assert res.correct_count == 4
    assert res.incorrect_count == 0
    assert res.unanswered_count == 0
    assert res.score_percentage == 100.0
    assert res.performance_grade == "A+"
    assert res.time_taken_formatted == "2m 0s"


def test_mixed_scoring_with_unanswered(scoring_service, sample_questions):
    """Test mixed answers including unanswered and wrong choices."""
    submission = QuizSubmission(
        quiz_id="test_quiz_2",
        time_taken_seconds=45,
        answers={
            "Q1": "A",  # Correct
            "Q2": "A",  # Incorrect (correct is B)
            # Q3 is unanswered
            "Q4": "C",  # Correct
        },
    )
    res = scoring_service.score_quiz(sample_questions, submission)
    assert res.total_questions == 4
    assert res.correct_count == 2
    assert res.incorrect_count == 1
    assert res.unanswered_count == 1
    assert res.score_percentage == 50.0  # 2 out of 4 is 50%
    # Accuracy on attempted (2 out of 3 answered is 66.7%)
    assert res.accuracy_rate == 66.7
    assert res.performance_grade == "D"


def test_zero_score(scoring_service, sample_questions):
    """Test 0% score when all questions are wrong or unanswered."""
    submission = QuizSubmission(
        quiz_id="test_quiz_3",
        time_taken_seconds=15,
        answers={"Q1": "D", "Q2": "D", "Q3": "D", "Q4": "D"},
    )
    res = scoring_service.score_quiz(sample_questions, submission)
    assert res.correct_count == 0
    assert res.incorrect_count == 4
    assert res.score_percentage == 0.0
    assert res.performance_grade == "F"


def test_topic_breakdown_calculation(scoring_service, sample_questions):
    """Test that topic performance is aggregated correctly."""
    submission = QuizSubmission(
        quiz_id="test_quiz_4",
        time_taken_seconds=30,
        answers={"Q1": "A", "Q2": "A", "Q3": "A", "Q4": "C"},
    )
    res = scoring_service.score_quiz(sample_questions, submission)
    topics = {t.topic: t for t in res.topic_breakdowns}

    assert "Activation Functions" in topics
    assert topics["Activation Functions"].accuracy_percentage == 100.0

    assert "Regularization" in topics
    assert topics["Regularization"].accuracy_percentage == 0.0
