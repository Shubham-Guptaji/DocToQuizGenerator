"""AI-powered personalized educational feedback and rule-based fallback generator."""
from typing import Dict, List, Optional
from models.schemas import AIFeedback, QuizResult
from services.ai_provider import BaseAIProvider, get_ai_provider
from utils.logging_config import get_logger

logger = get_logger("feedback_service")


class FeedbackService:
    """Generates educational analysis, weak topic diagnostics, and improvement roadmaps."""

    def __init__(self, ai_provider: Optional[BaseAIProvider] = None):
        self.ai_provider = ai_provider or get_ai_provider()

    def generate_feedback(
        self,
        result: QuizResult,
        document_context: Optional[str] = None,
    ) -> AIFeedback:
        """
        Generate personalized learning recommendations.
        Attempts AI analysis first; falls back to deterministic rule-based analysis.
        """
        try:
            return self._generate_ai_feedback(result, document_context)
        except Exception as e:
            logger.warning(f"AI feedback generation failed ({e}); invoking rule-based fallback.")
            return self.generate_fallback_feedback(result)

    def _generate_ai_feedback(
        self,
        result: QuizResult,
        document_context: Optional[str] = None,
    ) -> AIFeedback:
        """Query Gemini structured model with performance stats and wrong answers."""
        # Compile topic summary
        topic_summary = "\n".join([
            f"- {t.topic}: {t.correct_count}/{t.total_questions} ({t.accuracy_percentage}%)"
            for t in result.topic_breakdowns
        ])

        # Compile incorrect question details
        mistakes = [
            f"Question {r.question_id} [{r.topic}]: '{r.question}'\n"
            f"  User selected: {r.selected_answer or 'Unanswered'}, Correct: {r.correct_answer}\n"
            f"  Explanation: {r.explanation}"
            for r in result.reviews if not r.is_correct
        ]
        mistakes_text = "\n".join(mistakes[:15]) if mistakes else "None! Perfect score on all questions."

        prompt = f"""
STUDENT PERFORMANCE SUMMARY:
- Total Questions: {result.total_questions}
- Correct: {result.correct_count}
- Incorrect: {result.incorrect_count}
- Unanswered: {result.unanswered_count}
- Score: {result.score_percentage}%
- Grade: {result.performance_grade}

TOPIC BREAKDOWN:
{topic_summary}

MISTAKES AND MISCONCEPTIONS DETECTED:
{mistakes_text}

TASK:
Based strictly on the student's actual performance above, generate a comprehensive, personalized educational feedback report.
1. Provide an honest overall assessment.
2. Identify strongest topics (high accuracy) and weak topics (frequent errors or unanswered).
3. Analyze common mistakes and cognitive traps seen in their wrong choices.
4. Provide a numbered, prioritized revision plan.
5. Suggest practical follow-up practice activities.
6. Provide constructive encouragement tailored to their grade.
"""

        system_instruction = (
            "You are an empathetic, world-class academic tutor and test preparation specialist. "
            "Analyze student results accurately without fabricating weaknesses that are not supported by the data."
        )

        return self.ai_provider.generate_structured(
            prompt=prompt,
            schema_cls=AIFeedback,
            system_instruction=system_instruction,
        )

    def generate_fallback_feedback(self, result: QuizResult) -> AIFeedback:
        """
        Deterministic, rule-based learning feedback generator.
        Operates completely offline without external API calls.
        """
        # Classify topics by accuracy
        strong_topics = [t.topic for t in result.topic_breakdowns if t.accuracy_percentage >= 75.0]
        weak_topics = [t.topic for t in result.topic_breakdowns if t.accuracy_percentage < 60.0]
        moderate_topics = [t.topic for t in result.topic_breakdowns if 60.0 <= t.accuracy_percentage < 75.0]

        if not strong_topics:
            strong_topics = ["Fundamental factual recall"] if result.correct_count > 0 else ["Effort in attempting the quiz"]
        if not weak_topics:
            weak_topics = moderate_topics if moderate_topics else ["Advanced edge cases and nuanced questions"]

        # Analyze errors
        mistakes_observed = []
        if result.unanswered_count > 0:
            mistakes_observed.append(
                f"{result.unanswered_count} question(s) were left unanswered. Work on time management or process of elimination."
            )
        if result.incorrect_count > 0:
            mistakes_observed.append(
                "Mistakes primarily occurred in questions testing subtle conceptual distinctions and specific terms."
            )
        else:
            mistakes_observed.append("No notable mistakes observed. Complete mastery demonstrated across tested concepts.")

        # Revision plan
        revision_plan = [
            f"1. Priority Review: Re-read the source document sections covering {', '.join(weak_topics[:2])}.",
            "2. Active Recall: Write down definitions and core formulas without looking at notes.",
            "3. Question Review: Carefully examine the explanations for every missed question in the Detailed Review section.",
            "4. Retest: Use the 'Retry Incorrect Questions' option to test retention of previously missed items.",
        ]

        follow_up = [
            "Create a 1-page summary sheet of key definitions and exceptions from the document.",
            "Teach the most challenging concept from your weak topics to a peer or speak it aloud.",
            "Attempt another quiz on 'Hard' or 'Mixed' difficulty once revision is complete.",
        ]

        if result.score_percentage >= 85:
            assessment = (
                f"Superb performance! You achieved {result.score_percentage}%, showing a command of the core "
                f"subject matter. You have a solid grasp of key principles and answered {result.correct_count} "
                f"out of {result.total_questions} questions correctly."
            )
            encouragement = "You're in great shape for examinations! Keep your knowledge fresh with occasional quick reviews."
        elif result.score_percentage >= 65:
            assessment = (
                f"Solid effort! You scored {result.score_percentage}% ({result.correct_count}/{result.total_questions} correct). "
                f"You have a working foundation, but certain targeted areas need reinforcement."
            )
            encouragement = "A brief targeted revision session focused on your weaker topics will easily raise your score to the next tier!"
        else:
            assessment = (
                f"Good initial diagnostic attempt ({result.score_percentage}%). This quiz highlighted the critical areas "
                f"where source material should be reviewed thoroughly."
            )
            encouragement = "Every mistake is a learning opportunity. Focus on the prioritized revision plan and you will see rapid gains!"

        return AIFeedback(
            overall_assessment=assessment,
            strongest_topics=strong_topics,
            weak_topics=weak_topics,
            common_mistakes=mistakes_observed,
            prioritized_revision_plan=revision_plan,
            suggested_follow_up_activities=follow_up,
            encouragement=encouragement,
        )
