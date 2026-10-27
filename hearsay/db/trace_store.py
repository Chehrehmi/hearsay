"""
hearsay.db.trace_store: SQLite Audit & Trace Store for Hearsay verification telemetry.
"""

import sqlite3
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict, Any, Union

from hearsay.proxy.protocol import VerificationResult


class TraceStore:
    """
    SQLite-backed audit store for Hearsay verification requests, claim verdicts,
    groundedness scores, and latency metrics.
    """

    def __init__(self, db_path: Union[str, Path] = "hearsay_traces.db"):
        self.db_path = str(db_path)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Returns a connection configured with sqlite3.Row factory for dict-like access."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Initializes the database schema and performance indexes if they do not exist."""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS traces (
                    request_id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    source_id TEXT NOT NULL,
                    response_text TEXT NOT NULL,
                    overall_status TEXT NOT NULL,
                    groundedness_score REAL NOT NULL,
                    total_claims INTEGER NOT NULL,
                    supported_claims INTEGER NOT NULL,
                    contradicted_claims INTEGER NOT NULL,
                    ungrounded_claims INTEGER NOT NULL,
                    latency_ms REAL NOT NULL,
                    result_json TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_traces_timestamp 
                ON traces(timestamp DESC)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_traces_status 
                ON traces(overall_status)
            """)
    
    def log_trace(
    self,
    result: Union[VerificationResult, Dict[str, Any]],
    response_text: str,
    source_id: str,
    ) -> str:
        """
        Persists a verification result, associated response prose, and source ID.
        Accepts either a Pydantic VerificationResult instance or a dictionary.
        Returns the request_id.
        """
        if isinstance(result, VerificationResult):
            data = result.model_dump()
            result_json = result.model_dump_json()
        elif isinstance(result, dict):
            data = result
            result_json = json.dumps(result)
        else:
            raise TypeError("result must be an instance of VerificationResult or a dictionary.")

        request_id = str(data["request_id"])
        timestamp = datetime.now(timezone.utc).isoformat()

        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO traces (
                    request_id, timestamp, source_id, response_text,
                    overall_status, groundedness_score, total_claims,
                    supported_claims, contradicted_claims, ungrounded_claims,
                    latency_ms, result_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    request_id,
                    timestamp,
                    source_id,
                    response_text,
                    data.get("overall_status", "Unknown"),
                    float(data.get("groundedness_score", 0.0)),
                    int(data.get("total_claims", 0)),
                    int(data.get("supported_claims", 0)),
                    int(data.get("contradicted_claims", 0)),
                    int(data.get("ungrounded_claims", 0)),
                    float(data.get("latency_ms", 0.0)),
                    result_json,
                ),
            )

        return request_id

    def get_trace(self, request_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a single trace by ID, deserializing the result_json payload."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM traces WHERE request_id = ?", (request_id,)
            ).fetchone()

        if not row:
            return None

        record = dict(row)
        record["result"] = json.loads(record["result_json"])
        return record

    def get_recent_traces(
        self, limit: int = 50, offset: int = 0, status_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieves recent traces ordered by timestamp descending.
        Supports pagination (limit, offset) and optional status filtering.
        """
        query = "SELECT * FROM traces"
        params: List[Any] = []

        if status_filter:
            query += " WHERE overall_status = ?"
            params.append(status_filter)

        query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        with self._get_connection() as conn:
            rows = conn.execute(query, tuple(params)).fetchall()

        traces = []
        for row in rows:
            record = dict(row)
            record["result"] = json.loads(record["result_json"])
            traces.append(record)

        return traces

    def get_metrics_summary(self) -> Dict[str, Any]:
        """
        Computes aggregate telemetry metrics across all stored traces.
        Powers the observability dashboard KPI metric cards.
        """
        with self._get_connection() as conn:
            row = conn.execute(
                """
                SELECT 
                    COUNT(*) AS total_requests,
                    COALESCE(AVG(groundedness_score), 0.0) AS avg_groundedness,
                    COALESCE(AVG(latency_ms), 0.0) AS avg_latency_ms,
                    SUM(CASE WHEN overall_status = 'Verified' THEN 1 ELSE 0 END) AS total_verified,
                    SUM(CASE WHEN overall_status = 'Hallucination Detected' THEN 1 ELSE 0 END) AS total_hallucinations,
                    COALESCE(SUM(total_claims), 0) AS total_claims,
                    COALESCE(SUM(supported_claims), 0) AS total_supported,
                    COALESCE(SUM(contradicted_claims), 0) AS total_contradicted,
                    COALESCE(SUM(ungrounded_claims), 0) AS total_ungrounded
                FROM traces
                """
            ).fetchone()

        if not row or row["total_requests"] == 0:
            return {
                "total_requests": 0,
                "verification_pass_rate": 0.0,
                "avg_groundedness_score": 0.0,
                "avg_latency_ms": 0.0,
                "p50_latency_ms": 0.0,
                "p95_latency_ms": 0.0,
                "total_verified": 0,
                "total_hallucinations": 0,
                "total_claims": 0,
                "total_supported": 0,
                "total_contradicted": 0,
                "total_ungrounded": 0,
            }

        percentiles = self.get_latency_percentiles()
        total_req = int(row["total_requests"])
        total_ver = int(row["total_verified"] or 0)
        pass_rate = round((total_ver / total_req * 100.0), 2) if total_req > 0 else 0.0

        return {
            "total_requests": total_req,
            "verification_pass_rate": pass_rate,
            "avg_groundedness_score": round(float(row["avg_groundedness"]), 2),
            "avg_latency_ms": round(float(row["avg_latency_ms"]), 2),
            "p50_latency_ms": percentiles["p50"],
            "p95_latency_ms": percentiles["p95"],
            "total_verified": total_ver,
            "total_hallucinations": int(row["total_hallucinations"] or 0),
            "total_claims": int(row["total_claims"]),
            "total_supported": int(row["total_supported"]),
            "total_contradicted": int(row["total_contradicted"]),
            "total_ungrounded": int(row["total_ungrounded"]),
        }


    def get_latency_percentiles(self) -> Dict[str, float]:
        """
        Computes P50 (median), P90, P95, and P99 latency percentiles across stored traces.
        Essential for detecting long-tail inference latency spikes in production RAG systems.
        """
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT latency_ms FROM traces ORDER BY latency_ms ASC"
            ).fetchall()

        if not rows:
            return {"p50": 0.0, "p90": 0.0, "p95": 0.0, "p99": 0.0, "count": 0}

        latencies = [float(r["latency_ms"]) for r in rows]
        n = len(latencies)

        def _calc_percentile(p: float) -> float:
            k = (n - 1) * (p / 100.0)
            f = int(k)
            c = f + 1
            if c < n:
                return round(latencies[f] + (k - f) * (latencies[c] - latencies[f]), 2)
            return round(latencies[f], 2)

        return {
            "p50": _calc_percentile(50),
            "p90": _calc_percentile(90),
            "p95": _calc_percentile(95),
            "p99": _calc_percentile(99),
            "count": n,
        }


    def clear_traces(self) -> int:
        """Deletes all traces from the table. Returns number of rows deleted."""
        with self._get_connection() as conn:
            cursor = conn.execute("DELETE FROM traces")
            deleted = cursor.rowcount
        return deleted
