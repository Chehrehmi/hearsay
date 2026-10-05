import pytest
from fastapi.testclient import TestClient
from hearsay.proxy.gateway import app

client=TestClient(app)


def test_health_endpoint():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_verify_success_with_body():
    response = client.post(
        "/verify",
        json={
            "response_text": "Paris is the capital of France.",
            "verirag_context": {
                "source_info": "Paris is the capital of France.",
                "source_id": "test_doc_1",
            },
        },
    )

    assert response.status_code == 200
    assert response.json()["overall_status"] == "Verified"
    assert response.json()["groundedness_score"] == 100.0



def test_verify_success_with_headers():
    response = client.post(
        "/verify",
        headers={
            "X-Hearsay-Context": "Paris is the capital of France.",
            "X-Hearsay-Source-ID": "test_id",
        },
        json={
            "response_text": "Paris is the capital of France.",
        },
    )

    assert response.status_code == 200
    assert response.json()["claims"][0]["source_chunk_id"] == "test_id"

def test_verify_missing_inputs_returns_400():
    # Empty response_text
    response = client.post(
        "/verify",
        json={
            "response_text": "",
            "verirag_context": {
                "source_info": "Paris is the capital of France.",
                "source_id": "test_doc_1",
            },
        },
    )

    assert response.status_code == 400

    # Missing context
    response = client.post(
        "/verify",
        json={
            "response_text": "Paris is the capital of France.",
        },
    )

    assert response.status_code == 400

def test_verify_detects_hallucination():
    response = client.post(
        "/verify",
        json={
            "response_text": "Berlin is the capital of France.",
            "verirag_context": {
                "source_info": "Paris is the capital of France.",
                "source_id": "test_doc_1",
            },
        },
    )

    assert response.status_code == 200
    assert response.json()["overall_status"] == "Hallucination Detected"
    assert response.json()["groundedness_score"] == 0.0


def test_chat_completions_with_context_headers():
    response = client.post(
        "/v1/chat/completions",
        headers={
            "X-Hearsay-Context": "Paris is the capital of France.",
            "X-Hearsay-Source-ID": "test_id",
        },
        json={
            "model": "gpt-3.5-turbo",
            "messages": [
                {
                    "role": "user",
                    "content": "What is the capital of France?",
                }
            ],
            "response_text": "Paris is the capital of France.",
        },
    )

    assert response.status_code == 200
    assert response.headers["X-Hearsay-Status"] == "Verified"
    assert response.headers["X-Hearsay-Score"] == "100.0"
    assert response.json()["choices"][0]["message"]["role"] == "assistant"
    assert "hearsay_verification" in response.json()



def test_chat_completions_without_context():
    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "gpt-3.5-turbo",
            "messages": [
                {
                    "role": "user",
                    "content": "What is the capital of France?",
                }
            ],
            "response_text": "Paris is the capital of France.",
        },
    )

    assert response.status_code == 200
    assert response.headers["X-Hearsay-Status"] == "Unverified (No Context)"

def test_chat_completions_with_body_context():
    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "gpt-3.5-turbo",
            "messages": [{"role": "user", "content": "What is Paris?"}],
            "response_text": "Paris is in France.",
            "verirag_context": {
                "source_id": "doc_body_1",
                "source_info": "Paris is in France."
            }
        },
    )
    assert response.status_code == 200
    assert response.headers["X-Hearsay-Status"] == "Verified"
    assert response.json()["choices"][0]["message"]["content"] == "Paris is in France."



def test_verify_with_legacy_verirag_headers():
    response = client.post(
        "/verify",
        headers={
            "X-VeriRAG-Context": "The Earth orbits the Sun.",
            "X-VeriRAG-Source-ID": "legacy_doc",
        },
        json={
            "response_text": "The Earth orbits the Sun.",
        },
    )
    assert response.status_code == 200
    assert response.json()["overall_status"] == "Verified"
    assert response.json()["claims"][0]["source_chunk_id"] == "legacy_doc"
