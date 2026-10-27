import json
from pathlib import Path
import pytest
from hearsay.eval.report_generator import (
    EvaluationReportGenerator,
    generate_ascii_bar,
    generate_evaluation_report,
)


def test_generate_ascii_bar():
    bar = generate_ascii_bar(0.80, width=10)
    assert "80.0%" in bar
    assert "█" in bar
    assert "░" in bar


def test_evaluation_report_generator(tmp_path):
    sample_data = {
        "samples_evaluated": 15,
        "total_sentences": 42,
        "split": "test",
        "task_type": "all",
        "metrics": {"precision": 0.88, "recall": 0.82, "f1": 0.849, "accuracy": 0.91},
        "per_task_metrics": {
            "Summary": {"count": 10, "precision": 0.90, "recall": 0.85, "f1": 0.874, "accuracy": 0.93},
            "QA": {"count": 5, "precision": 0.84, "recall": 0.78, "f1": 0.809, "accuracy": 0.88},
        },
        "latency_profile": {
            "mean_ms": 18.5,
            "min_ms": 8.0,
            "max_ms": 42.0,
            "p50_ms": 16.0,
            "p90_ms": 32.0,
            "p95_ms": 38.0,
            "p99_ms": 41.0,
        },
        "detailed_records": [
            {
                "sentence": "The price increased by 10%.",
                "y_true": 0,
                "y_pred": 0,
                "task_type": "Summary",
                "confidence": 0.95,
                "source_snippet": "Context",
            },
            {
                "sentence": "A new product launched in 2025.",
                "y_true": 1,
                "y_pred": 1,
                "task_type": "QA",
                "confidence": 0.90,
                "source_snippet": "Context",
            },
        ],
    }

    generator = EvaluationReportGenerator(sample_data)
    report_md = generator.generate_report_markdown()

    assert "HEARSAY: Week 1 MVP Final Evaluation & Benchmark Report" in report_md
    assert "Quantitative Groundedness Performance" in report_md
    assert "Latency Profile & SLA Compliance" in report_md
    assert "Summary" in report_md
    assert "QA" in report_md

    out_file = tmp_path / "EVALUATION_REPORT.md"
    generator.save_report(str(out_file))
    assert out_file.exists()


def test_generate_evaluation_report_from_file(tmp_path):
    sample_data = {
        "samples_evaluated": 5,
        "total_sentences": 12,
        "metrics": {"precision": 1.0, "recall": 1.0, "f1": 1.0, "accuracy": 1.0},
        "per_task_metrics": {},
        "latency_profile": {"mean_ms": 10.0, "p50_ms": 9.0, "p95_ms": 15.0},
        "detailed_records": [],
    }

    json_path = tmp_path / "results.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(sample_data, f)

    gen = EvaluationReportGenerator.from_file(json_path)
    md = gen.generate_report_markdown()
    assert "Executive Summary & Sprint Acceptance" in md

    out_md = tmp_path / "EVALUATION_REPORT.md"
    generate_evaluation_report(sample_data, str(out_md))
    assert out_md.exists()
