"""Unit and integration tests for Hearsay TraceStore database module."""

import pytest
import sqlite3
from hearsay.db import TraceStore
from hearsay.proxy.protocol import VerificationResult, ClaimVerdict


@pytest.fixture
def store(tmp_path):
    """Provides a fresh, isolated TraceStore instance using a temporary database."""
    db_file = tmp_path / "test_hearsay.db"
    return TraceStore(db_path=db_file)


@pytest.fixture
def sample_result():
    """Provides a valid Pydantic VerificationResult for testing."""
    return VerificationResult(
        request_id="req-12345",
        overall_status="Verified",
        groundedness_score=100.0,
        total_claims=1,
        supported_claims=1,
        contradicted_claims=0,
        ungrounded_claims=0,
        claims=[
            ClaimVerdict(
                claim_id=0,
                claim_text="Paris is in France.",
                status="Supported",
                confidence=0.98,
                evidence_span="Paris is the capital of France.",
                source_chunk_id="chunk_01",
            )
        ],
        latency_ms=15.4,
    )


def test_db_initialization(store):
    """Tests that the database tables and indexes are created properly."""
    with store._get_connection() as conn:
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='traces'"
        ).fetchall()
        assert len(tables) == 1

        indexes = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index'"
        ).fetchall()
        index_names = [idx["name"] for idx in indexes]
        assert "idx_traces_timestamp" in index_names
        assert "idx_traces_status" in index_names


def test_log_and_get_trace_pydantic(store, sample_result):
    """Tests logging a Pydantic VerificationResult and retrieving it by ID."""
    req_id = store.log_trace(
        result=sample_result,
        response_text="Paris is in France.",
        source_id="doc_geo_01",
    )
    assert req_id == "req-12345"

    trace = store.get_trace("req-12345")
    assert trace is not None
    assert trace["request_id"] == "req-12345"
    assert trace["source_id"] == "doc_geo_01"
    assert trace["response_text"] == "Paris is in France."
    assert trace["overall_status"] == "Verified"
    assert trace["groundedness_score"] == 100.0
    assert trace["result"]["total_claims"] == 1
    assert trace["result"]["claims"][0]["confidence"] == 0.98


def test_log_trace_dict(store):
    """Tests logging a raw dictionary verification payload."""
    raw_payload = {
        "request_id": "req-dict-01",
        "overall_status": "Hallucination Detected",
        "groundedness_score": 0.0,
        "total_claims": 1,
        "supported_claims": 0,
        "contradicted_claims": 0,
        "ungrounded_claims": 1,
        "claims": [],
        "latency_ms": 22.1,
    }
    req_id = store.log_trace(
        result=raw_payload,
        response_text="London is in Germany.",
        source_id="doc_geo_02",
    )
    assert req_id == "req-dict-01"

    trace = store.get_trace("req-dict-01")
    assert trace is not None
    assert trace["overall_status"] == "Hallucination Detected"
    assert trace["groundedness_score"] == 0.0


def test_log_trace_invalid_type(store):
    """Tests that passing an invalid type raises TypeError."""
    with pytest.raises(TypeError):
        store.log_trace(result="not a result", response_text="text", source_id="src")


def test_get_nonexistent_trace(store):
    """Tests that querying a missing request_id returns None."""
    assert store.get_trace("nonexistent-id") is None


def test_get_recent_traces_and_filtering(store, sample_result):
    """Tests listing recent traces with pagination and status filtering."""
    # 1. Log verified trace
    store.log_trace(sample_result, "Paris is in France.", "doc_1")

    # 2. Log hallucinated trace
    hallucination_payload = {
        "request_id": "req-hallucinated",
        "overall_status": "Hallucination Detected",
        "groundedness_score": 0.0,
        "total_claims": 1,
        "supported_claims": 0,
        "contradicted_claims": 0,
        "ungrounded_claims": 1,
        "claims": [],
        "latency_ms": 10.0,
    }
    store.log_trace(hallucination_payload, "Fake response", "doc_2")

    # Retrieve all (limit 10)
    all_traces = store.get_recent_traces(limit=10)
    assert len(all_traces) == 2

    # Filter by Verified
    verified_only = store.get_recent_traces(status_filter="Verified")
    assert len(verified_only) == 1
    assert verified_only[0]["request_id"] == "req-12345"

    # Filter by Hallucination Detected
    hallucinated_only = store.get_recent_traces(status_filter="Hallucination Detected")
    assert len(hallucinated_only) == 1
    assert hallucinated_only[0]["request_id"] == "req-hallucinated"


def test_metrics_summary(store, sample_result):
    """Tests SQL aggregation metrics across empty and populated databases."""
    # Empty DB
    empty_summary = store.get_metrics_summary()
    assert empty_summary["total_requests"] == 0
    assert empty_summary["verification_pass_rate"] == 0.0

    # Log 1 Verified (100% grounded, 10ms)
    sample_result.latency_ms = 10.0
    store.log_trace(sample_result, "Sample text 1", "doc_1")

    # Log 1 Hallucinated (0% grounded, 30ms)
    hallucinated = {
        "request_id": "req-hallu",
        "overall_status": "Hallucination Detected",
        "groundedness_score": 0.0,
        "total_claims": 2,
        "supported_claims": 0,
        "contradicted_claims": 1,
        "ungrounded_claims": 1,
        "claims": [],
        "latency_ms": 30.0,
    }
    store.log_trace(hallucinated, "Sample text 2", "doc_2")

    summary = store.get_metrics_summary()
    assert summary["total_requests"] == 2
    assert summary["total_verified"] == 1
    assert summary["total_hallucinations"] == 1
    assert summary["verification_pass_rate"] == 50.0
    assert summary["avg_groundedness_score"] == 50.0  # (100 + 0) / 2
    assert summary["avg_latency_ms"] == 20.0          # (10 + 30) / 2
    assert summary["total_claims"] == 3               # 1 + 2


def test_clear_traces(store, sample_result):
    """Tests clearing all traces."""
    store.log_trace(sample_result, "Text", "doc_1")
    assert len(store.get_recent_traces()) == 1

    deleted = store.clear_traces()
    assert deleted == 1
    assert len(store.get_recent_traces()) == 0


def test_latency_percentiles(store, sample_result):
    """Tests P50, P90, P95, P99 percentile calculations."""
    # Empty DB
    empty_p = store.get_latency_percentiles()
    assert empty_p["p50"] == 0.0
    assert empty_p["p95"] == 0.0
    assert empty_p["count"] == 0

    # Log 5 traces with latencies: 10, 20, 30, 40, 50 ms
    for lat in [10.0, 20.0, 30.0, 40.0, 50.0]:
        t = {
            "request_id": f"req-lat-{lat}",
            "overall_status": "Verified",
            "groundedness_score": 100.0,
            "total_claims": 1,
            "supported_claims": 1,
            "contradicted_claims": 0,
            "ungrounded_claims": 0,
            "claims": [],
            "latency_ms": lat,
        }
        store.log_trace(t, "Sample", "doc_1")

    p = store.get_latency_percentiles()
    assert p["count"] == 5
    assert p["p50"] == 30.0   # Median
    assert p["p90"] == 46.0   # 90th percentile
    assert p["p95"] == 48.0   # 95th percentile
    assert p["p99"] == 49.6   # 99th percentile

    summary = store.get_metrics_summary()
    assert summary["p50_latency_ms"] == 30.0
    assert summary["p95_latency_ms"] == 48.0


