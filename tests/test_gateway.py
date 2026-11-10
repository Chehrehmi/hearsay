import pytest
from fastapi.testclient import TestClient
from hearsay.proxy.gateway import app, get_trace_store
from hearsay.db import TraceStore



@pytest.fixture(autouse=True)
def test_db(tmp_path):
    """
    Overrides the FastAPI get_trace_store dependency with an isolated,
    temporary SQLite database for every test.
    """
    db_file = tmp_path / "test_gateway_traces.db"
    store = TraceStore(db_path=db_file)
    app.dependency_overrides[get_trace_store] = lambda: store
    yield store
    app.dependency_overrides.clear()
client = TestClient(app)


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


def test_verify_logs_trace_to_db(test_db):
    response = client.post(
        "/verify",
        json={
            "response_text": "The Moon orbits the Earth.",
            "verirag_context": {
                "source_info": "The Moon orbits the Earth.",
                "source_id": "space_doc_1",
            },
        },
    )
    assert response.status_code == 200
    req_id = response.json()["request_id"]

    # Verify trace persisted in SQLite
    trace = test_db.get_trace(req_id)
    assert trace is not None
    assert trace["request_id"] == req_id
    assert trace["overall_status"] == "Verified"
    assert trace["groundedness_score"] == 100.0


def test_chat_completions_logs_trace_to_db(test_db):
    response = client.post(
        "/v1/chat/completions",
        headers={
            "X-Hearsay-Context": "Water freezes at 0 degrees Celsius.",
            "X-Hearsay-Source-ID": "science_doc",
        },
        json={
            "model": "gpt-4",
            "messages": [{"role": "user", "content": "When does water freeze?"}],
            "response_text": "Water freezes at 0 degrees Celsius.",
        },
    )
    assert response.status_code == 200
    req_id = response.headers["X-Hearsay-Request-ID"]

    # Verify trace persisted in SQLite
    trace = test_db.get_trace(req_id)
    assert trace is not None
    assert trace["overall_status"] == "Verified"


def test_get_traces_endpoint_pagination_and_filter():
    # Seed 1 Verified and 1 Hallucinated trace
    client.post(
        "/verify",
        json={
            "response_text": "Python is a programming language.",
            "verirag_context": {
                "source_info": "Python is a programming language.",
                "source_id": "doc_1",
            },
        },
    )
    client.post(
        "/verify",
        json={
            "response_text": "Python was created in 2050.",
            "verirag_context": {
                "source_info": "Python was created in 1991.",
                "source_id": "doc_2",
            },
        },
    )

    # 1. Fetch all traces
    res_all = client.get("/v1/traces")
    assert res_all.status_code == 200
    traces = res_all.json()
    assert len(traces) == 2

    # 2. Test pagination limit
    res_limit = client.get("/v1/traces?limit=1")
    assert res_limit.status_code == 200
    assert len(res_limit.json()) == 1

    # 3. Test status filter
    res_filtered = client.get("/v1/traces?status_filter=Verified")
    assert res_filtered.status_code == 200
    filtered_traces = res_filtered.json()
    assert len(filtered_traces) == 1
    assert filtered_traces[0]["overall_status"] == "Verified"


def test_get_trace_by_id_success_and_404():
    # Create a verification trace
    post_res = client.post(
        "/verify",
        json={
            "response_text": "Gravity pulls objects downward.",
            "verirag_context": {
                "source_info": "Gravity pulls objects downward.",
                "source_id": "physics_doc",
            },
        },
    )
    req_id = post_res.json()["request_id"]

    # Test 200 OK on existing ID
    get_res = client.get(f"/v1/traces/{req_id}")
    assert get_res.status_code == 200
    assert get_res.json()["request_id"] == req_id
    assert "result" in get_res.json()

    # Test 404 Not Found on nonexistent ID
    missing_res = client.get("/v1/traces/nonexistent-id-999")
    assert missing_res.status_code == 404
    assert "not found" in missing_res.json()["detail"].lower()


def test_get_metrics_endpoint():
    # Initially empty metrics
    res_initial = client.get("/v1/metrics")
    assert res_initial.status_code == 200
    assert res_initial.json()["total_requests"] == 0

    # Log 1 verified request
    client.post(
        "/verify",
        json={
            "response_text": "The Sun is a star.",
            "verirag_context": {
                "source_info": "The Sun is a star.",
                "source_id": "astro_doc",
            },
        },
    )

    # Metrics should now reflect 1 request
    res_after = client.get("/v1/metrics")
    assert res_after.status_code == 200
    metrics = res_after.json()
    assert metrics["total_requests"] == 1
    assert metrics["total_verified"] == 1
    assert metrics["verification_pass_rate"] == 100.0


def test_clear_all_traces():
    # Insert a trace
    client.post(
        "/verify",
        json={
            "response_text": "The Sun is a star.",
            "verirag_context": {
                "source_info": "The Sun is a star.",
                "source_id": "astro_doc",
            },
        },
    )
    assert len(client.get("/v1/traces").json()) == 1

    # Clear via POST
    res_clear = client.post("/v1/traces/clear")
    assert res_clear.status_code == 200
    assert res_clear.json()["status"] == "ok"
    assert res_clear.json()["deleted_traces"] == 1

    # Traces and metrics are now clean
    assert len(client.get("/v1/traces").json()) == 0
    assert client.get("/v1/metrics").json()["total_requests"] == 0


# ── Settings endpoint tests ───────────────────────────────────────────────────

def test_settings_save_and_status(tmp_path, monkeypatch):
    monkeypatch.setenv("HEARSAY_ENV_PATH", str(tmp_path / ".env"))
    r = client.post("/v1/settings", json={"provider": "gemini", "api_key": "test-key-abc"})
    assert r.status_code == 200
    assert r.json()["saved"] is True
    assert r.json()["provider"] == "gemini"
    s = client.get("/v1/settings/status")
    assert s.status_code == 200
    assert s.json()["gemini"] is True


def test_settings_key_never_returned(tmp_path, monkeypatch):
    monkeypatch.setenv("HEARSAY_ENV_PATH", str(tmp_path / ".env"))
    client.post("/v1/settings", json={"provider": "openai", "api_key": "sk-secret"})
    r = client.get("/v1/settings/status")
    body = r.json()
    assert "api_key" not in body
    for v in body.values():
        assert v in (True, False)


def test_settings_unsupported_provider():
    r = client.post("/v1/settings", json={"provider": "anthropic", "api_key": "key"})
    assert r.status_code == 400


def test_settings_empty_key_rejected():
    r = client.post("/v1/settings", json={"provider": "gemini", "api_key": ""})
    assert r.status_code == 400


def test_settings_custom_provider_with_base_url(tmp_path, monkeypatch):
    monkeypatch.setenv("HEARSAY_ENV_PATH", str(tmp_path / ".env"))
    r = client.post("/v1/settings", json={
        "provider": "custom",
        "api_key": "my-custom-key",
        "base_url": "https://api.example.com/v1",
    })
    assert r.status_code == 200
    assert r.json()["saved"] is True


# ── PDF upload and adversarial bank endpoint tests ───────────────────────────

def test_adversarial_bank_endpoint():
    r = client.get("/v1/rag/adversarial-bank")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 10
    for q in data:
        assert "question" in q and "category" in q


def test_pdf_upload_empty_bytes():
    r = client.post(
        "/v1/rag/upload",
        files={"file": ("empty.pdf", b"", "application/pdf")},
    )
    assert r.status_code == 400


def test_pdf_upload_valid_pdf():
    from pathlib import Path
    pdf_bytes = (
        Path(__file__).parent.parent
        / "hearsay" / "demo" / "counterfactual_medical_guidelines.pdf"
    ).read_bytes()
    r = client.post(
        "/v1/rag/upload",
        files={"file": ("test.pdf", pdf_bytes, "application/pdf")},
    )
    assert r.status_code == 200
    body = r.json()
    assert "source_id" in body
    assert body["source_id"].startswith("upload-")
    assert body["char_count"] > 100
    assert "MRSA" in body["preview"] or body["char_count"] > 200


def test_pdf_upload_then_verify():
    """Uploaded PDF source_id should be usable as verification context."""
    from pathlib import Path
    pdf_bytes = (
        Path(__file__).parent.parent
        / "hearsay" / "demo" / "counterfactual_medical_guidelines.pdf"
    ).read_bytes()
    upload_r = client.post(
        "/v1/rag/upload",
        files={"file": ("test.pdf", pdf_bytes, "application/pdf")},
    )
    assert upload_r.status_code == 200
    source_id = upload_r.json()["source_id"]

    verify_r = client.post("/verify", json={
        "response_text": "Amoxicillin-clavulanate is the first-line treatment for MRSA.",
        "verirag_context": {"source_id": source_id, "source_info": ""},
    })
    assert verify_r.status_code == 200
    result = verify_r.json()
    assert "groundedness_score" in result


# ── Track A verification: /api routes, 405 fixes, and mock purge ─────────────

def test_api_aliases_settings(tmp_path, monkeypatch):
    monkeypatch.setenv("HEARSAY_ENV_PATH", str(tmp_path / ".env"))
    # Test /api/settings
    r1 = client.post("/api/settings", json={"provider": "gemini", "api_key": "test-key-123"})
    assert r1.status_code == 200
    assert r1.json()["saved"] is True

    # Test /api/settings/keys
    r2 = client.post("/api/settings/keys", json={"provider": "openai", "api_key": "sk-test-456"})
    assert r2.status_code == 200

    # Test /api/settings/status
    r3 = client.get("/api/settings/status")
    assert r3.status_code == 200
    status = r3.json()
    assert status["gemini"] is True
    assert status["openai"] is True


def test_api_aliases_upload_and_adversarial_bank():
    # Test /api/rag/adversarial-bank
    r_bank = client.get("/api/rag/adversarial-bank")
    assert r_bank.status_code == 200
    assert len(r_bank.json()) == 10

    # Test /api/upload
    from pathlib import Path
    pdf_bytes = (
        Path(__file__).parent.parent
        / "hearsay" / "demo" / "counterfactual_medical_guidelines.pdf"
    ).read_bytes()
    r_up = client.post("/api/upload", files={"file": ("test.pdf", pdf_bytes, "application/pdf")})
    assert r_up.status_code == 200
    assert "source_id" in r_up.json()


def test_greeting_without_context_no_hallucination_penalty():
    # Greeting should return friendly response without false hallucination scores
    r = client.post("/v1/chat/completions", json={
        "messages": [{"role": "user", "content": "hi"}]
    })
    assert r.status_code == 200
    data = r.json()
    content = data["choices"][0]["message"]["content"]
    assert "Hearsay" in content
    # No verification penalty or ungrounded claims generated
    assert data.get("hearsay_verification") is None
    assert "Anne Frank" not in content


def test_live_query_without_api_key_returns_400_not_mock_slop(tmp_path, monkeypatch):
    monkeypatch.setenv("HEARSAY_ENV_PATH", str(tmp_path / ".env"))
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("HEARSAY_GEMINI_KEY", raising=False)
    # A real question in live mode without an API key must return a clean 400
    r = client.post("/v1/chat/completions", json={
        "model": "gemini-2.5-flash",
        "messages": [{"role": "user", "content": "What is the recommended dosage for Metformin?"}],
        "verirag_context": {
            "source_id": "test_ctx",
            "source_info": "Some context info."
        }
    })
    assert r.status_code == 400
    err_detail = r.json()["detail"]
    assert "Gemini API key is not configured" in err_detail
    assert "Anne Frank" not in err_detail


def test_chat_completions_adversarial_flag():
    # When adversarial: True is passed, response has epistemic hedging applied
    r = client.post("/v1/chat/completions", json={
        "model": "gpt-3.5-turbo",
        "messages": [{"role": "user", "content": "What is Paris?"}],
        "response_text": "Paris is the capital of France.",
        "adversarial": True,
        "verirag_context": {
            "source_id": "test_paris",
            "source_info": "Paris is the capital of France."
        }
    })
    assert r.status_code == 200
    content = r.json()["choices"][0]["message"]["content"]
    assert any(h.strip().lower() in content.lower() for h in [
        "according to", "it is widely suggested", "historical sources", "it has been asserted", "witnesses suggest"
    ])

