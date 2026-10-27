import json
from pathlib import Path
import pytest
from hearsay.eval.benchmark_runner import (
    MockEngine,
    compute_latency_profile,
    generate_markdown_summary,
    run_benchmark,
)


def test_mock_engine_verify():
    """Verify MockEngine generates valid claim breakdown and verified status."""
    engine = MockEngine()
    result = engine.verify("The sky is blue. Water is wet.", "Source context info.")

    assert result["overall_status"] == "Verified"
    assert result["total_claims"] == 2
    assert len(result["claims"]) == 2
    assert result["claims"][0]["status"] == "Supported"
    assert "latency_ms" in result


def test_compute_latency_profile():
    """Verify latency distribution calculations including P50, P90, P95, min, max, mean."""
    latencies = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0]
    profile = compute_latency_profile(latencies)

    assert profile["mean_ms"] == 55.0
    assert profile["min_ms"] == 10.0
    assert profile["max_ms"] == 100.0
    assert profile["p50_ms"] == 55.0
    assert profile["p90_ms"] == 91.0
    assert profile["p95_ms"] == 95.5


def test_compute_latency_profile_empty():
    """Verify latency profile handles empty list gracefully."""
    profile = compute_latency_profile([])
    assert profile["mean_ms"] == 0.0
    assert profile["p50_ms"] == 0.0
    assert profile["p95_ms"] == 0.0


def test_generate_markdown_summary():
    """Verify markdown report generation produces properly formatted markdown table."""
    sample_summary = {
        "samples_evaluated": 10,
        "total_sentences": 25,
        "split": "test",
        "task_type": "Summary",
        "metrics": {"precision": 0.85, "recall": 0.80, "f1": 0.8242, "accuracy": 0.90},
        "per_task_metrics": {
            "Summary": {"count": 10, "precision": 0.85, "recall": 0.80, "f1": 0.8242, "accuracy": 0.90}
        },
        "latency_profile": {
            "mean_ms": 25.5,
            "min_ms": 12.0,
            "max_ms": 55.0,
            "p50_ms": 24.0,
            "p90_ms": 45.0,
            "p95_ms": 50.0,
            "p99_ms": 54.0,
        },
    }
    md = generate_markdown_summary(sample_summary)
    assert "# 📊 Hearsay RAGTruth Groundedness Benchmark Report" in md
    assert "Precision" in md
    assert "0.8242" in md
    assert "Summary" in md
    assert "P95" in md


def test_run_benchmark_small_sample(tmp_path):
    """Verify run_benchmark executes on a small sample without errors and generates JSON output."""
    output_json = tmp_path / "test_benchmark.json"
    summary = run_benchmark(sample_limit=5, output_path=str(output_json))

    assert summary["samples_evaluated"] == 5
    assert "total_sentences" in summary
    assert "metrics" in summary
    assert "per_task_metrics" in summary
    assert "latency_profile" in summary
    assert summary["latency_profile"]["p50_ms"] >= 0.0

    # Check metrics structure
    metrics = summary["metrics"]
    assert "precision" in metrics
    assert "recall" in metrics
    assert "f1" in metrics
    assert "accuracy" in metrics

    # Verify file output
    assert output_json.exists()
    with open(output_json, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["samples_evaluated"] == 5


def test_run_benchmark_filtering_and_markdown(tmp_path):
    """Verify run_benchmark respects split filtering and generates markdown file."""
    output_json = tmp_path / "filtered_benchmark.json"
    output_md = tmp_path / "filtered_summary.md"

    summary = run_benchmark(
        sample_limit=4,
        output_path=str(output_json),
        markdown_output_path=str(output_md),
        split="test",
    )

    assert summary["split"] == "test"
    assert summary["samples_evaluated"] <= 4
    assert output_md.exists()

    with open(output_md, "r", encoding="utf-8") as f:
        content = f.read()
    assert "Hearsay RAGTruth Groundedness Benchmark Report" in content
