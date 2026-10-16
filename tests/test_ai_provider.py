"""Automated tests for AI Provider abstractions, Mock fallback, and missing key handling."""
import pytest
from models.schemas import AIFeedback, QuizQuestionsResponse
from services.ai_provider import AIProviderError, GeminiAIProvider, MockAIProvider, get_ai_provider


def test_mock_provider_quiz_generation():
    """Verify that MockAIProvider synthesizes schema-valid questions."""
    provider = MockAIProvider()
    assert provider.is_available
    assert "Mock" in provider.provider_name

    prompt = "Generate exactly 10 questions. Topic focus: Neural Networks"
    resp = provider.generate_structured(prompt, QuizQuestionsResponse)

    assert isinstance(resp, QuizQuestionsResponse)
    assert len(resp.questions) == 10
    for q in resp.questions:
        assert len(q.options) == 4
        assert q.correct_answer in {"A", "B", "C", "D"}
        assert q.explanation is not None


def test_mock_provider_feedback_generation():
    """Verify that MockAIProvider synthesizes valid educational feedback."""
    provider = MockAIProvider()
    resp = provider.generate_structured("Feedback prompt", AIFeedback)

    assert isinstance(resp, AIFeedback)
    assert len(resp.strongest_topics) > 0
    assert len(resp.weak_topics) > 0
    assert len(resp.prioritized_revision_plan) > 0
    assert resp.encouragement is not None


def test_gemini_provider_missing_key():
    """Verify that GeminiAIProvider without key reports unavailable and raises error on generate."""
    provider = GeminiAIProvider(api_key="")
    assert not provider.is_available

    with pytest.raises(AIProviderError) as exc_info:
        provider.generate_structured("test", QuizQuestionsResponse)
    assert "missing or invalid" in str(exc_info.value)


def test_get_ai_provider_factory():
    """Verify factory returns MockAIProvider when key is absent."""
    provider = get_ai_provider(force_mock=True)
    assert isinstance(provider, MockAIProvider)
