"""Automated tests for PDF validation, extraction, chunking, and scanned detection."""
from pathlib import Path
import pytest
from services.pdf_service import PDFService
from utils.validators import validate_pdf_file


@pytest.fixture
def pdf_service():
    return PDFService()


@pytest.fixture
def sample_pdf_bytes():
    path = Path("sample_docs/machine_learning_primer.pdf")
    assert path.exists(), "Sample PDF fixture missing."
    return path.read_bytes()


def test_valid_pdf_extraction(pdf_service, sample_pdf_bytes):
    """Test standard extraction from a valid educational PDF."""
    doc = pdf_service.process_pdf(sample_pdf_bytes, "machine_learning_primer.pdf")
    assert doc.error is None
    assert doc.page_count == 3
    assert doc.word_count > 100
    assert doc.char_count > 1000
    assert not doc.is_scanned
    assert 1 in doc.page_map
    assert 2 in doc.page_map
    assert 3 in doc.page_map
    assert "Supervised Learning" in doc.full_text
    assert "Backpropagation" in doc.full_text
    assert "Regularization" in doc.full_text


def test_invalid_extension(pdf_service):
    """Test rejection of non-PDF files."""
    doc = pdf_service.process_pdf(b"hello world", "notes.txt")
    assert doc.error is not None
    assert "Only PDF documents are supported" in doc.error


def test_empty_file(pdf_service):
    """Test rejection of empty 0-byte file."""
    doc = pdf_service.process_pdf(b"", "empty.pdf")
    assert doc.error is not None
    assert "empty (0 bytes)" in doc.error


def test_invalid_pdf_header(pdf_service):
    """Test rejection of files without PDF magic bytes."""
    doc = pdf_service.process_pdf(b"NOT_A_PDF_CONTENT_STREAM", "corrupt.pdf")
    assert doc.error is not None
    assert "Invalid PDF header" in doc.error


def test_context_selection_budget(pdf_service, sample_pdf_bytes):
    """Test text chunking and sampling for context limits."""
    doc = pdf_service.process_pdf(sample_pdf_bytes, "machine_learning_primer.pdf")
    context = pdf_service.select_context_for_generation(doc, max_chars=800)
    assert len(context) <= 1200
    assert "Page 1" in context
