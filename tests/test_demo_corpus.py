"""
Tests for Hearsay Curated Demo Corpus.
Ensures curated RAG scenarios for demo are valid, authentic, and non-empty.
"""

import pytest
from hearsay.demo.corpus import get_curated_rag_samples


def test_get_curated_rag_samples_returns_valid_entries():
    samples = get_curated_rag_samples()
    assert len(samples) >= 3
    for s in samples:
        assert "id" in s
        assert "title" in s
        assert "category" in s
        assert "question" in s
        assert "context" in s
        assert "expected_response" in s
        assert len(s["context"]) > 20
        assert len(s["question"]) > 5


def test_gateway_demo_corpus_endpoint():
    from fastapi.testclient import TestClient
    from hearsay.proxy.gateway import app
    client = TestClient(app)
    res = client.get("/v1/demo/corpus")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) >= 3
    assert data[0]["id"] == "scenario-anne-frank-faithful"


# ── Adversarial question bank tests ──────────────────────────────────────────

from hearsay.demo.adversarial_questions import get_adversarial_bank


def test_adversarial_bank_has_ten_questions():
    bank = get_adversarial_bank()
    assert len(bank) == 10


def test_adversarial_bank_schema():
    bank = get_adversarial_bank()
    required_keys = {"id", "category", "question", "expected_failure"}
    for q in bank:
        assert required_keys <= q.keys(), f"Missing keys in: {q}"
        assert q["category"] in {
            "parametric_conflict",
            "epistemic_hedging",
            "adversarial_paraphrase",
            "robustness",
        }, f"Unknown category: {q['category']}"


def test_adversarial_bank_ids_unique():
    bank = get_adversarial_bank()
    ids = [q["id"] for q in bank]
    assert len(ids) == len(set(ids)), "Duplicate IDs in adversarial bank"


def test_adversarial_bank_non_empty_fields():
    bank = get_adversarial_bank()
    for q in bank:
        assert len(q["question"]) > 20, f"Question too short: {q['id']}"
        assert len(q["expected_failure"]) > 10, f"expected_failure too short: {q['id']}"


# ── Counterfactual PDF tests ──────────────────────────────────────────────────

def test_counterfactual_pdf_exists_and_readable():
    import pdfplumber
    from pathlib import Path
    pdf_path = Path(__file__).parent.parent / "hearsay" / "demo" / "counterfactual_medical_guidelines.pdf"
    assert pdf_path.exists(), "Counterfactual PDF not found — run make_counterfactual_pdf.py"
    with pdfplumber.open(pdf_path) as f:
        text = "".join(p.extract_text() or "" for p in f.pages)
    assert "MRSA" in text
    assert "Metformin" in text
    assert "Aspirin" in text
    assert len(text) > 500
