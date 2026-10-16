"""Integration tests for FastAPI REST endpoints."""
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from api import app

client = TestClient(app)


def test_health_endpoint():
    """Verify health check endpoint returns 200 and system metadata."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "app_name" in data


def test_pdf_upload_endpoint():
    """Verify document upload and metadata extraction endpoint."""
    pdf_path = Path("sample_docs/machine_learning_primer.pdf")
    with open(pdf_path, "rb") as f:
        response = client.post(
            "/api/upload-pdf",
            files={"file": ("machine_learning_primer.pdf", f, "application/pdf")},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "machine_learning_primer.pdf"
    assert data["page_count"] == 3
    assert data["document_id"] is not None
    assert len(data["extracted_text_preview"]) > 0


def test_generate_and_submit_quiz_flow():
    """Verify end-to-end REST journey: upload -> generate -> submit -> view history."""
    # 1. Upload
    pdf_path = Path("sample_docs/machine_learning_primer.pdf")
    with open(pdf_path, "rb") as f:
        up_resp = client.post(
            "/api/upload-pdf",
            files={"file": ("machine_learning_primer.pdf", f, "application/pdf")},
        )
    doc_id = up_resp.json()["document_id"]

    # 2. Generate
    gen_payload = {
        "document_id": doc_id,
        "question_count": 5,
        "difficulty": "Medium",
        "topic_focus": "Neural Networks",
        "language": "English",
    }
    gen_resp = client.post("/api/generate-quiz", json=gen_payload)
    assert gen_resp.status_code == 200
    quiz_data = gen_resp.json()
    quiz_id = quiz_data["quiz_id"]
    questions = quiz_data["questions"]
    assert len(questions) > 0

    # 3. Submit
    submission_payload = {
        "quiz_id": quiz_id,
        "time_taken_seconds": 95,
        "answers": {q["question_id"]: "A" for q in questions},
    }
    sub_resp = client.post("/api/submit-quiz", json=submission_payload)
    assert sub_resp.status_code == 200
    result_data = sub_resp.json()
    assert result_data["total_questions"] == len(questions)
    assert "score_percentage" in result_data
    assert "performance_grade" in result_data
    assert len(result_data["reviews"]) == len(questions)

    # 4. History
    hist_resp = client.get("/api/history")
    assert hist_resp.status_code == 200
    attempts = hist_resp.json()
    assert len(attempts) > 0
    assert any(a["quiz_id"] == quiz_id for a in attempts)
