"""AI provider service wrapping the official Google Gen AI SDK with fallback and mock support."""
import abc
import json
import re
import time
from typing import Any, Dict, List, Optional, Type
from google import genai
from google.genai import types
from google.genai.errors import APIError
from pydantic import BaseModel
from config.settings import settings
from utils.logging_config import get_logger

logger = get_logger("ai_provider")


class AIProviderError(Exception):
    """Custom exception for AI provider communication or formatting errors."""
    pass


class BaseAIProvider(abc.ABC):
    """Abstract interface for AI generation providers."""

    @abc.abstractmethod
    def generate_structured(
        self,
        prompt: str,
        schema_cls: Type[BaseModel],
        system_instruction: Optional[str] = None,
    ) -> BaseModel:
        """Generate structured response validated against a Pydantic schema."""
        pass

    @abc.abstractmethod
    def generate_text(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
    ) -> str:
        """Generate freeform text."""
        pass

    @property
    @abc.abstractmethod
    def provider_name(self) -> str:
        """Name of the provider."""
        pass

    @property
    @abc.abstractmethod
    def is_available(self) -> bool:
        """Check if provider is configured and available."""
        pass


class GeminiAIProvider(BaseAIProvider):
    """Google Gemini AI integration using the official google-genai SDK."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key if api_key is not None else settings.GEMINI_API_KEY
        self.model = model or settings.GEMINI_MODEL
        self._client: Optional[genai.Client] = None

        if self.api_key:
            try:
                self._client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.error(f"Failed to initialize Gemini Client: {e}")
                self._client = None

    @property
    def provider_name(self) -> str:
        return f"Google Gemini ({self.model})"

    @property
    def is_available(self) -> bool:
        return bool(self._client and self.api_key and self.api_key != "your_gemini_api_key_here")

    def _clean_json_output(self, raw_text: str) -> str:
        """Extract and clean raw JSON from markdown fenced blocks if present."""
        clean = raw_text.strip()
        # Remove markdown code fences if model enclosed them
        if clean.startswith("```json"):
            clean = clean[7:]
        elif clean.startswith("```"):
            clean = clean[3:]
        if clean.endswith("```"):
            clean = clean[:-3]
        return clean.strip()

    def generate_structured(
        self,
        prompt: str,
        schema_cls: Type[BaseModel],
        system_instruction: Optional[str] = None,
    ) -> BaseModel:
        """Generate structured JSON adhering to the Pydantic schema with bounded retries."""
        if not self.is_available:
            raise AIProviderError(
                "Gemini API key is missing or invalid. Please configure GEMINI_API_KEY in your .env or Settings."
            )

        max_retries = settings.RATE_LIMIT_RETRIES
        delay = 2.0

        for attempt in range(1, max_retries + 1):
            try:
                logger.info(f"Generating structured content with model {self.model} (attempt {attempt}/{max_retries})")

                try:
                    config = types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=schema_cls,
                        system_instruction=system_instruction,
                    )
                    response = self._client.models.generate_content(
                        model=self.model,
                        contents=prompt,
                        config=config,
                    )
                except Exception as schema_err:
                    err_str = str(schema_err)
                    if "additionalProperties" in err_str or "schema" in err_str.lower() or "400" in err_str:
                        logger.warning(f"Gemini response_schema call encountered: {schema_err}. Executing prompt-schema fallback...")
                        schema_json = json.dumps(schema_cls.model_json_schema(), indent=2)
                        fallback_instruction = (
                            (system_instruction or "")
                            + f"\n\nCRITICAL: Respond ONLY with valid JSON strictly conforming to this schema:\n{schema_json}"
                        )
                        fallback_config = types.GenerateContentConfig(
                            response_mime_type="application/json",
                            system_instruction=fallback_instruction,
                        )
                        response = self._client.models.generate_content(
                            model=self.model,
                            contents=prompt,
                            config=fallback_config,
                        )
                    else:
                        raise schema_err

                output_text = response.text or ""
                cleaned_json = self._clean_json_output(output_text)
                validated_obj = schema_cls.model_validate_json(cleaned_json)
                return validated_obj

            except APIError as api_err:
                err_str = str(api_err)
                logger.warning(f"Gemini API error (attempt {attempt}): {api_err}")

                # If 503 high demand on primary model, attempt immediate failover to high-throughput flash-lite
                if ("503" in err_str or "UNAVAILABLE" in err_str or "high demand" in err_str.lower()) and self.model != "gemini-3.5-flash-lite":
                    logger.info("Model 503 high demand detected. Attempting failover to gemini-3.5-flash-lite...")
                    try:
                        config = types.GenerateContentConfig(
                            response_mime_type="application/json",
                            response_schema=schema_cls,
                            system_instruction=system_instruction,
                        )
                        response = self._client.models.generate_content(
                            model="gemini-3.5-flash-lite",
                            contents=prompt,
                            config=config,
                        )
                        output_text = response.text or ""
                        cleaned_json = self._clean_json_output(output_text)
                        return schema_cls.model_validate_json(cleaned_json)
                    except Exception as failover_err:
                        logger.warning(f"Failover attempt to gemini-3.5-flash-lite failed: {failover_err}")

                if attempt == max_retries:
                    raise AIProviderError(f"Gemini API error after {max_retries} attempts: {api_err}")
                time.sleep(delay)
                delay *= 2
            except Exception as e:
                logger.warning(f"Generation attempt {attempt} failed: {e}")
                if attempt == max_retries:
                    raise AIProviderError(f"Failed to generate structured data from Gemini: {e}")
                time.sleep(delay)
                delay *= 2

        raise AIProviderError("Exhausted retries without a valid response from Gemini.")

    def generate_text(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
    ) -> str:
        """Generate text using Gemini model with retries."""
        if not self.is_available:
            raise AIProviderError("Gemini API key is missing or invalid.")

        max_retries = settings.RATE_LIMIT_RETRIES
        delay = 2.0

        for attempt in range(1, max_retries + 1):
            try:
                config = types.GenerateContentConfig(
                    system_instruction=system_instruction,
                )
                response = self._client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=config,
                )
                return response.text or ""
            except Exception as e:
                logger.warning(f"Text generation attempt {attempt} failed: {e}")
                if attempt == max_retries:
                    raise AIProviderError(f"Failed to generate text from Gemini: {e}")
                time.sleep(delay)
                delay *= 2

        return ""


class MockAIProvider(BaseAIProvider):
    """
    Mock AI Provider for automated offline testing and graceful local fallback.
    Produces high-fidelity, grounded questions and feedback.
    """

    @property
    def provider_name(self) -> str:
        return "Local Mock Provider (Offline / Testing)"

    @property
    def is_available(self) -> bool:
        return True

    def generate_structured(
        self,
        prompt: str,
        schema_cls: Type[BaseModel],
        system_instruction: Optional[str] = None,
    ) -> BaseModel:
        """Synthesize schema-compliant mock data grounded in the prompt."""
        from models.schemas import AIFeedback, QuestionItem, QuizQuestionsResponse

        # Case 1: Quiz generation request
        if schema_cls == QuizQuestionsResponse:
            # Parse requested question count from prompt if possible
            count_match = re.search(r"Generate exactly (\d+) questions", prompt)
            target_count = int(count_match.group(1)) if count_match else 10
            # Cap realistic mock count between 5 and 50
            target_count = min(target_count, 50)

            # Extract subject clues from prompt
            topic = "General Knowledge"
            if "Topic focus:" in prompt:
                m = re.search(r"Topic focus:\s*([^\n\r]+)", prompt)
                if m:
                    topic = m.group(1).strip()

            questions: List[QuestionItem] = []
            for i in range(1, target_count + 1):
                correct_letter = ["A", "B", "C", "D"][(i - 1) % 4]
                difficulty = ["Easy", "Medium", "Hard"][(i - 1) % 3]

                q = QuestionItem(
                    question_id=f"Q{i}",
                    question=f"According to the source document, which statement correctly describes concept #{i} regarding {topic}?",
                    options={
                        "A": f"It is directly defined in the core text as an essential foundational principle (Concept #{i}).",
                        "B": f"It is classified as an optional secondary observation with no operational impact.",
                        "C": f"It was refuted by empirical findings discussed in later sections.",
                        "D": f"It applies strictly to hypothetical models without real-world validation.",
                    },
                    correct_answer=correct_letter,
                    explanation=f"Option {correct_letter} is correct because the source document establishes this principle as a foundational element of {topic}.",
                    topic=f"{topic} - Section {(i % 5) + 1}",
                    difficulty=difficulty,
                    source_reference=f"Page {(i % 8) + 1}",
                )
                questions.append(q)

            return QuizQuestionsResponse(questions=questions)

        # Case 2: AI Feedback request
        if schema_cls == AIFeedback:
            return AIFeedback(
                overall_assessment=(
                    "You demonstrated a solid general grasp of the document material, "
                    "with particular strengths in core definitions and direct factual questions. "
                    "Refining analytical and multi-step reasoning questions will help push your score to mastery."
                ),
                strongest_topics=[
                    "Foundational concepts and terminology",
                    "Direct factual identification",
                    "Core architectural workflows",
                ],
                weak_topics=[
                    "Edge case handling and error conditions",
                    "Comparative evaluation between alternative methods",
                ],
                common_mistakes=[
                    "Confusing secondary implementation details with primary architectural principles",
                    "Rushing through multi-clause questions with tricky distractors",
                ],
                prioritized_revision_plan=[
                    "1. Re-read the source document sections covering comparative analysis and edge cases.",
                    "2. Create concise flashcards for key definitions and boundary conditions.",
                    "3. Re-attempt the incorrect questions to solidify understanding.",
                    "4. Practice timed revision sessions to improve question pacing.",
                ],
                suggested_follow_up_activities=[
                    "Summarize the main differences between the primary concepts in your own words.",
                    "Draft 3 custom challenge questions and verify them against the source document pages.",
                    "Retake the quiz focusing strictly on eliminating distractors first.",
                ],
                encouragement="Great effort on this quiz! Consistent review and targeted practice on your weaker areas will yield substantial improvement on your next attempt.",
            )

        raise AIProviderError(f"Mock provider does not have a template for {schema_cls.__name__}")

    def generate_text(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
    ) -> str:
        return "This is a simulated AI response generated by the local mock provider."


def get_ai_provider(force_mock: bool = False) -> BaseAIProvider:
    """Factory function returning the active AI provider based on configuration."""
    if force_mock:
        return MockAIProvider()

    if settings.has_gemini_api_key:
        provider = GeminiAIProvider()
        if provider.is_available:
            return provider

    logger.warning("No valid Gemini API key found. Falling back to MockAIProvider.")
    return MockAIProvider()
