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
