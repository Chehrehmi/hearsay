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
