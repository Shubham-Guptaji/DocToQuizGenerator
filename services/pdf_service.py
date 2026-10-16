"""PDF text extraction, validation, chunking, and scanned document detection."""
import io
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from config.settings import settings
from utils.logging_config import get_logger
from utils.validators import sanitize_prompt_injection, validate_pdf_file

logger = get_logger("pdf_service")

# Try importing fitz (PyMuPDF)
try:
    import fitz  # PyMuPDF
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False

# Try importing pypdf
try:
    import pypdf
    HAS_PYPDF = True
except ImportError:
    HAS_PYPDF = False


@dataclass
class ExtractedDocument:
    """Encapsulates the parsed PDF data and extraction metadata."""
    filename: str
    file_size_bytes: int
    page_count: int
    char_count: int
    word_count: int
    extracted_text_preview: str
    full_text: str
    page_map: Dict[int, str] = field(default_factory=dict)  # 1-indexed page_num -> page_text
    is_scanned: bool = False
    error: Optional[str] = None


class PDFService:
    """Handles PDF validation, extraction, chunking, and pre-processing."""

    def __init__(self):
        if not HAS_PYMUPDF and not HAS_PYPDF:
            logger.warning("Neither PyMuPDF nor pypdf is installed.")

    def process_pdf(self, file_bytes: bytes, filename: str) -> ExtractedDocument:
        """
        Validate and extract text from an uploaded PDF document.
        Handles encrypted, corrupted, and scanned files.
        """
        # Step 1: Pre-flight validation
        is_valid, error_msg = validate_pdf_file(filename, file_bytes)
        if not is_valid:
            return ExtractedDocument(
                filename=filename,
                file_size_bytes=len(file_bytes),
                page_count=0,
                char_count=0,
                word_count=0,
                extracted_text_preview="",
                full_text="",
                error=error_msg,
            )

        # Step 2: Attempt extraction with PyMuPDF, then fallback to pypdf
        page_map: Dict[int, str] = {}
        error_encountered: Optional[str] = None
        page_count = 0

        if HAS_PYMUPDF:
            try:
                doc = fitz.open(stream=file_bytes, filetype="pdf")
                if doc.is_encrypted:
                    return ExtractedDocument(
                        filename=filename,
                        file_size_bytes=len(file_bytes),
                        page_count=0,
                        char_count=0,
                        word_count=0,
                        extracted_text_preview="",
                        full_text="",
                        error="The PDF file is password-protected or encrypted. Please provide an unencrypted PDF.",
                    )

                page_count = len(doc)
                for page_idx in range(page_count):
                    page = doc[page_idx]
                    page_text = page.get_text() or ""
                    page_map[page_idx + 1] = page_text
                doc.close()
            except Exception as e:
                logger.warning(f"PyMuPDF extraction failed: {e}. Falling back to pypdf.")
                error_encountered = str(e)

        # Fallback to pypdf if PyMuPDF wasn't available or failed
        if (not page_map or error_encountered) and HAS_PYPDF:
            try:
                reader = pypdf.PdfReader(io.BytesIO(file_bytes))
                if reader.is_encrypted:
                    return ExtractedDocument(
                        filename=filename,
                        file_size_bytes=len(file_bytes),
                        page_count=0,
                        char_count=0,
                        word_count=0,
                        extracted_text_preview="",
                        full_text="",
                        error="The PDF file is password-protected. Please provide an unencrypted document.",
                    )

                page_count = len(reader.pages)
                page_map = {}
                for idx, page in enumerate(reader.pages):
                    page_text = page.extract_text() or ""
                    page_map[idx + 1] = page_text
                error_encountered = None
            except Exception as e:
                logger.error(f"pypdf extraction failed: {e}")
                error_encountered = f"Unable to read PDF: {e}"

        if error_encountered:
            return ExtractedDocument(
                filename=filename,
                file_size_bytes=len(file_bytes),
                page_count=page_count,
                char_count=0,
                word_count=0,
                extracted_text_preview="",
                full_text="",
                error=error_encountered,
            )

        # Step 3: Combine and sanitize extracted text
        full_text_parts = []
        for p_num in sorted(page_map.keys()):
            p_text = page_map[p_num].strip()
            if p_text:
                full_text_parts.append(f"--- Page {p_num} ---\n{p_text}")

        raw_combined = "\n\n".join(full_text_parts).strip()
        sanitized_text = sanitize_prompt_injection(raw_combined)

        char_count = len(sanitized_text)
        words = sanitized_text.split()
        word_count = len(words)

        # Step 4: Detect scanned or empty PDF
        is_scanned = False
        if page_count > 0 and (char_count < 35 or word_count < 8):
            is_scanned = True
            error_msg = (
                "This document appears to be a scanned image or contains no selectable digital text. "
                "Optical Character Recognition (OCR) is required to parse scanned documents."
            )
            return ExtractedDocument(
                filename=filename,
                file_size_bytes=len(file_bytes),
                page_count=page_count,
                char_count=char_count,
                word_count=word_count,
                extracted_text_preview=sanitized_text[:500],
                full_text=sanitized_text,
                page_map=page_map,
                is_scanned=True,
                error=error_msg,
            )

        preview = sanitized_text[:1200] + ("..." if len(sanitized_text) > 1200 else "")

        return ExtractedDocument(
            filename=filename,
            file_size_bytes=len(file_bytes),
            page_count=page_count,
            char_count=char_count,
            word_count=word_count,
            extracted_text_preview=preview,
            full_text=sanitized_text,
            page_map=page_map,
            is_scanned=False,
            error=None,
        )

    def select_context_for_generation(
        self,
        extracted_doc: ExtractedDocument,
        max_chars: Optional[int] = None,
    ) -> str:
        """
        Prepare representative text context from the document.
        For large documents exceeding limit, evenly samples pages across the beginning,
        middle, and end so questions reflect the entire source material.
        """
        max_chars = max_chars or settings.MAX_DOCUMENT_CHARS_TO_SEND

        if len(extracted_doc.full_text) <= max_chars:
            return extracted_doc.full_text

        # Distribute budget across pages
        pages = extracted_doc.page_map
        if not pages:
            return extracted_doc.full_text[:max_chars]

        total_pages = len(pages)
        chars_per_page_budget = max(500, max_chars // total_pages)

        selected_parts = []
        current_len = 0

        for p_num in sorted(pages.keys()):
            p_text = pages[p_num].strip()
            if not p_text:
                continue

            # Take up to chars_per_page_budget
            snippet = p_text[:chars_per_page_budget]
            formatted_snippet = f"--- Page {p_num} ---\n{snippet}"

            if current_len + len(formatted_snippet) > max_chars:
                break

            selected_parts.append(formatted_snippet)
            current_len += len(formatted_snippet)

        return "\n\n".join(selected_parts)
