import json
from pathlib import Path
import pytest
from hearsay.eval.benchmark_runner import run_benchmark, MockEngine


def test_mock_engine_verify():
    """Verify MockEngine generates valid claim breakdown and verified status."""
    engine = MockEngine()
    result = engine.verify("The sky is blue. Water is wet.", "Source context info.")
    
    assert result["overall_status"] == "Verified"
    assert result["total_claims"] == 2
    assert len(result["claims"]) == 2
    assert result["claims"][0]["status"] == "Supported"
    assert "latency_ms" in result


def test_run_benchmark_small_sample(tmp_path):
    """Verify run_benchmark executes on a small sample without errors and generates JSON output."""
    output_json = tmp_path / "test_benchmark.json"
    summary = run_benchmark(sample_limit=5, output_path=str(output_json))
    
    assert summary["samples_evaluated"] == 5
    assert "total_sentences" in summary
    assert "metrics" in summary
    assert "per_task_metrics" in summary
    assert "avg_latency_ms" in summary
    
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
