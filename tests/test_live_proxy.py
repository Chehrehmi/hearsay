"""
Tests for Hearsay Chat Completions Live Proxy and Verification Middleware.
"""

import os
os.environ["HF_HUB_OFFLINE"] = "1"

import pytest
from fastapi.testclient import TestClient
from hearsay.proxy.gateway import app

client = TestClient(app)


def test_chat_completions_with_explicit_response_verifies_and_logs():
    payload = {
        "model": "hearsay-verified",
        "messages": [
            {"role": "user", "content": "When did Anne Frank die?"}
        ],
        "response_text": "Anne Frank died in March 1945 in Bergen-Belsen.",
        "verirag_context": {
            "source_id": "doc-anne-frank",
            "text": "Seventy years ago, Anne Frank died of typhus in a Nazi concentration camp at the age of 15 in March 1945."
        }
    }
    res = client.post("/v1/chat/completions", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "hearsay_verification" in data
    assert data["hearsay_verification"]["overall_status"] in ["Verified", "Hallucination Detected"]
    assert "choices" in data
    assert len(data["choices"]) > 0
    assert data["choices"][0]["message"]["content"] == payload["response_text"]


def test_chat_completions_offline_context_extraction():
    # When response_text is omitted, gateway extracts an answer from context
    payload = {
        "model": "hearsay-verified",
        "messages": [
            {"role": "user", "content": "Tell me about Bergen Belsen."}
        ],
        "verirag_context": {
            "source_id": "doc-test",
            "text": "Bergen-Belsen was liberated in April 1945 by British armed forces."
        }
    }
    res = client.post("/v1/chat/completions", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "hearsay_verification" in data
    content = data["choices"][0]["message"]["content"]
    assert len(content) > 0
    assert data["hearsay_verification"]["overall_status"] in ["Verified", "Hallucination Detected"]
