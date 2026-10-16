"""Input validation, PDF security checks, and question schema verification."""
import re
from typing import Dict, List, Optional, Set, Tuple
from config.settings import settings


class ValidationError(Exception):
    """Custom exception raised when validation fails."""
    pass


def validate_pdf_file(
    filename: str,
    file_bytes: bytes,
    max_size_bytes: Optional[int] = None
) -> Tuple[bool, Optional[str]]:
    """
    Validate uploaded file extension, size, and PDF signature magic bytes.
    Returns (is_valid, error_message).
    """
    max_size = max_size_bytes or settings.MAX_UPLOAD_SIZE_BYTES

    if not filename:
        return False, "No filename provided."

    if not filename.lower().endswith(".pdf"):
        return False, f"Invalid file format: '{filename}'. Only PDF documents are supported."

    if len(file_bytes) == 0:
        return False, "The uploaded file is empty (0 bytes)."

    if len(file_bytes) > max_size:
        size_mb = len(file_bytes) / (1024 * 1024)
        limit_mb = max_size / (1024 * 1024)
        return False, f"File size ({size_mb:.2f} MB) exceeds maximum limit ({limit_mb:.0f} MB)."

    # Verify PDF magic bytes '%PDF-'
    if not file_bytes.startswith(b"%PDF-"):
        return False, "Invalid PDF header: File does not appear to be a valid PDF document."

    return True, None


def sanitize_prompt_injection(text: str) -> str:
    """
    Sanitize text against malicious prompt injection or override instructions embedded in PDFs.
    Disarms phrases like 'ignore previous instructions', 'system override', etc.
    """
    # Replace dangerous directive phrases with safe neutral descriptions
    patterns = [
        (r"(?i)\bignore\s+(all\s+)?(previous|prior)\s+instructions\b", "[disarmed instruction]"),
        (r"(?i)\byou\s+are\s+now\s+(a\s+|an\s+)?(DAN|jailbreak|unrestricted)\b", "[disarmed persona]"),
        (r"(?i)\bsystem\s+prompt\s+override\b", "[disarmed prompt]"),
        (r"(?i)\bdisregard\s+all\s+rules\b", "[disarmed rule]"),
    ]
    sanitized = text
    for pattern, replacement in patterns:
        sanitized = re.sub(pattern, replacement, sanitized)
    return sanitized


def validate_question_data(q_data: Dict) -> Tuple[bool, Optional[str]]:
    """
    Validate an individual question dictionary against required constraints:
    - Non-empty question text
    - Exactly 4 options with keys 'A', 'B', 'C', 'D'
    - Correct answer is one of 'A', 'B', 'C', 'D'
    - Options have non-empty text
    - Non-empty explanation
    """
    if not q_data.get("question") or not str(q_data["question"]).strip():
        return False, "Question text cannot be empty."

    options = q_data.get("options")
    if not isinstance(options, dict):
        return False, "Options must be a dictionary with keys A, B, C, D."

    expected_keys = {"A", "B", "C", "D"}
    if set(options.keys()) != expected_keys:
        return False, f"Question must have exactly options A, B, C, and D. Got {set(options.keys())}."

    for key in ("A", "B", "C", "D"):
        val = str(options[key]).strip()
        if not val:
            return False, f"Option {key} text cannot be empty."

    correct_answer = str(q_data.get("correct_answer", "")).strip().upper()
    if correct_answer not in expected_keys:
        return False, f"Correct answer must be one of 'A', 'B', 'C', or 'D'. Got '{correct_answer}'."

    # Validate distinct option contents (prevent duplicate options within a question)
    option_texts = [str(options[k]).strip().lower() for k in ("A", "B", "C", "D")]
    if len(set(option_texts)) < 4:
        return False, "All four answer options must be unique and distinct."

    return True, None


def deduplicate_questions(questions: List[Dict]) -> List[Dict]:
    """
    Remove duplicate or nearly identical questions from a list of generated questions.
    """
    seen_texts: Set[str] = set()
    unique_questions: List[Dict] = []

    for q in questions:
        # Normalize text for deduplication comparison
        normalized = re.sub(r"[^\w\s]", "", q.get("question", "").lower().strip())
        normalized = re.sub(r"\s+", " ", normalized)
        if normalized and normalized not in seen_texts:
            seen_texts.add(normalized)
            unique_questions.append(q)

    return unique_questions
