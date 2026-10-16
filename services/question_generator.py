"""MCQ generation orchestrator applying difficulty prompts, chunking, and validation."""
from typing import List, Optional, Tuple
from config.settings import settings
from models.schemas import (
    DifficultyLevel,
    QuestionItem,
    QuizConfig,
    QuizQuestionsResponse,
)
from services.ai_provider import BaseAIProvider, get_ai_provider
from services.pdf_service import ExtractedDocument, PDFService
from utils.logging_config import get_logger
from utils.validators import deduplicate_questions, validate_question_data

logger = get_logger("question_generator")


class QuestionGeneratorService:
    """Orchestrates MCQ extraction and validation from PDF content."""

    def __init__(self, ai_provider: Optional[BaseAIProvider] = None, pdf_service: Optional[PDFService] = None):
        self.ai_provider = ai_provider or get_ai_provider()
        self.pdf_service = pdf_service or PDFService()

    def _build_system_instruction(self, language: str = "English") -> str:
        return (
            f"You are a master academic assessment designer and exam creator. "
            f"Your mission is to generate high-quality, rigorous Multiple Choice Questions (MCQs) in {language} "
            f"strictly grounded in the provided document text. "
            f"Rules:\n"
            f"1. Generate questions ONLY from the facts, concepts, definitions, and data in the provided document text.\n"
            f"2. Never use external general knowledge not verified in the document.\n"
            f"3. Each question must have exactly four distinct options labeled A, B, C, and D.\n"
            f"4. Exactly one option must be unambiguously correct. Avoid 'All of the above' or 'None of the above'.\n"
            f"5. The three distractors must be plausible, competitive, and related to the domain, but strictly incorrect based on the text.\n"
            f"6. Provide a concise explanation specifying why the correct answer is true and citing the source page where found.\n"
            f"7. Strictly adhere to the requested difficulty tier."
        )

    def _build_difficulty_prompt(self, difficulty: DifficultyLevel, count: int) -> str:
        if difficulty == DifficultyLevel.EASY:
            return (
                f"Generate {count} EASY difficulty questions focusing on clear definitions, direct facts, "
                f"terminology, and straightforward comprehension directly stated in the text."
            )
        elif difficulty == DifficultyLevel.MEDIUM:
            return (
                f"Generate {count} MEDIUM difficulty questions requiring conceptual understanding, comparison "
                f"between components, contextual interpretation, and direct application of principles."
            )
        elif difficulty == DifficultyLevel.HARD:
            return (
                f"Generate {count} HARD difficulty questions requiring multi-step reasoning, synthesis across "
                f"different sections, identifying edge cases, nuanced distinctions, and challenging distractors."
            )
        else:  # MIXED
            easy_c = max(1, count // 3)
            hard_c = max(1, count // 3)
            med_c = count - easy_c - hard_c
            return (
                f"Generate {count} MIXED difficulty questions with a balanced distribution: "
                f"approximately {easy_c} Easy questions (definitions/facts), {med_c} Medium questions "
                f"(conceptual/comparative), and {hard_c} Hard questions (multi-step reasoning/analysis). "
                f"Explicitly set the 'difficulty' field to 'Easy', 'Medium', or 'Hard' for each."
            )

    def generate_quiz_questions(
        self,
        extracted_doc: ExtractedDocument,
        config: QuizConfig,
    ) -> Tuple[List[QuestionItem], Optional[str]]:
        """
        Generate, validate, and deduplicate questions from the extracted document.
        Returns (list_of_valid_questions, warning_or_error_message).
        """
        if extracted_doc.error:
            return [], f"Cannot generate quiz: {extracted_doc.error}"

        if not extracted_doc.full_text or extracted_doc.char_count < 100:
            return [], "The document does not contain sufficient readable text to generate meaningful questions."

        # Step 1: Select balanced context across pages
        context_text = self.pdf_service.select_context_for_generation(extracted_doc)

        # Check if the document has enough text for high question counts
        est_words = extracted_doc.word_count
        target_count = config.question_count
        note_message: Optional[str] = None

        if est_words < target_count * 15:
            # Short document limitation warning
            note_message = (
                f"The uploaded document is concise ({est_words} words). "
                f"To maintain question accuracy without hallucination, questions will be generated "
                f"strictly from the available material."
            )

        # Step 2: Assemble prompt
        diff_instruction = self._build_difficulty_prompt(config.difficulty, target_count)
        topic_clause = f"\nTopic focus: {config.topic_focus}" if config.topic_focus else ""

        user_prompt = f"""
DOCUMENT SOURCE TEXT:
\"\"\"
{context_text}
\"\"\"

TASK:
Generate exactly {target_count} multiple-choice questions (MCQs) in {config.language} based strictly on the document text above.
{diff_instruction}
{topic_clause}

REQUIREMENTS:
- Each question must have question_id like "Q1", "Q2", etc.
- Options dictionary MUST have exact keys "A", "B", "C", "D".
- correct_answer must be either "A", "B", "C", or "D".
- Provide clear explanation and cite source page number where possible (e.g. "Page 2").
- Assign a specific topic or concept name to the 'topic' field.
- Ensure all 4 options are distinct and plausible.
"""

        system_instruction = self._build_system_instruction(config.language)

        try:
            response: QuizQuestionsResponse = self.ai_provider.generate_structured(
                prompt=user_prompt,
                schema_cls=QuizQuestionsResponse,
                system_instruction=system_instruction,
            )
        except Exception as e:
            logger.error(f"AI generation failed: {e}")
            return [], f"Quiz generation failed: {e}"

        # Step 3: Validate and sanitize each generated question
        valid_questions: List[QuestionItem] = []
        raw_list = [q.model_dump() for q in response.questions]

        # Deduplicate
        deduped = deduplicate_questions(raw_list)

        for idx, q_dict in enumerate(deduped, start=1):
            is_valid, err = validate_question_data(q_dict)
            if is_valid:
                # Ensure sequential ID
                q_dict["question_id"] = f"Q{idx}"
                try:
                    item = QuestionItem(**q_dict)
                    valid_questions.append(item)
                except Exception as val_err:
                    logger.warning(f"Skipping question due to model validation error: {val_err}")
            else:
                logger.warning(f"Skipping invalid question: {err}")

        if not valid_questions:
            return [], "Failed to generate valid questions meeting all quality and schema constraints."

        logger.info(f"Successfully generated {len(valid_questions)} validated questions (requested {target_count})")
        return valid_questions, note_message
