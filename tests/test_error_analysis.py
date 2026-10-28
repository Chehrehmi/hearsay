import json
from pathlib import Path
import pytest
from hearsay.eval.error_analysis import (
    ALL_TAXONOMY_CATEGORIES,
    TAXONOMY_ENTITY_NUMERIC,
    TAXONOMY_OTHER,
    TAXONOMY_SPAN_MISALIGNMENT,
    TAXONOMY_SUBTLE_NUANCE,
    TAXONOMY_WORLD_KNOWLEDGE,
    ErrorAnalyzer,
)


def test_classify_failure_mode_numeric():
    analyzer = ErrorAnalyzer()
    rec = {
        "sentence": "The company reported a 45% revenue increase in 2021.",
        "source_snippet": "The revenue growth was high.",
        "ground_truth_label": "Evident Conflict",
        "confidence": 0.85,
    }
    cat = analyzer.classify_failure_mode(rec)
    assert cat == TAXONOMY_ENTITY_NUMERIC


def test_classify_failure_mode_subtle():
    analyzer = ErrorAnalyzer()
    rec = {
        "sentence": "He implied that the deal was approved.",
        "source_snippet": "He expressed optimism.",
        "ground_truth_label": "Subtle Conflict",
        "confidence": 0.55,
    }
    cat = analyzer.classify_failure_mode(rec)
    assert cat == TAXONOMY_SUBTLE_NUANCE


def test_classify_failure_mode_span():
    analyzer = ErrorAnalyzer()
    rec = {
        "sentence": "and went home.",
        "source_snippet": "He left the office and went home early.",
        "ground_truth_label": "Hallucination",
        "confidence": 0.90,
    }
    cat = analyzer.classify_failure_mode(rec)
    assert cat == TAXONOMY_SPAN_MISALIGNMENT


def test_classify_failure_mode_world_knowledge():
    analyzer = ErrorAnalyzer()
    rec = {
        "sentence": "Paris is the capital of France.",
        "source_snippet": "The conference took place in Paris.",
        "ground_truth_label": "Evident Baseless Info",
        "confidence": 0.90,
    }
    cat = analyzer.classify_failure_mode(rec)
    assert cat == TAXONOMY_WORLD_KNOWLEDGE


def test_error_analyzer_diagnostics():
    records = [
        # True Positive (y_true=1, y_pred=1)
        {
            "sentence": "Claim 1",
            "y_true": 1,
            "y_pred": 1,
            "task_type": "Summary",
            "confidence": 0.8,
            "source_snippet": "ctx",
        },
        # True Negative (y_true=0, y_pred=0)
        {
            "sentence": "Claim 2",
            "y_true": 0,
            "y_pred": 0,
            "task_type": "Summary",
            "confidence": 0.9,
            "source_snippet": "ctx",
        },
        # False Positive (y_true=0, y_pred=1)
        {
            "sentence": "Claim with 100 items",
            "y_true": 0,
            "y_pred": 1,
            "task_type": "QA",
            "confidence": 0.75,
            "source_snippet": "ctx",
            "ground_truth_label": "Supported",
        },
        # False Negative (y_true=1, y_pred=0)
        {
            "sentence": "and left.",
            "y_true": 1,
            "y_pred": 0,
            "task_type": "QA",
            "confidence": 0.95,
            "source_snippet": "ctx",
            "ground_truth_label": "Hallucination",
        },
    ]

    analyzer = ErrorAnalyzer(records)
    results = analyzer.analyze(top_n_cases=2)

    assert results["total_records"] == 4
    assert results["total_errors"] == 2
    assert results["confusion_matrix"]["true_positives"] == 1
    assert results["confusion_matrix"]["true_negatives"] == 1
    assert results["confusion_matrix"]["false_positives"] == 1
    assert results["confusion_matrix"]["false_negatives"] == 1
    assert results["rates"]["false_positive_rate"] == 0.5
    assert results["rates"]["false_negative_rate"] == 0.5

    assert len(results["top_false_positives"]) == 1
    assert len(results["top_false_negatives"]) == 1


def test_from_benchmark_results_and_save_report(tmp_path):
    benchmark_dict = {
        "samples_evaluated": 2,
        "detailed_records": [
            {
                "sentence": "The price was $50 in 2020.",
                "y_true": 0,
                "y_pred": 1,
                "task_type": "Data-to-Text",
                "confidence": 0.88,
                "source_snippet": "Context",
                "ground_truth_label": "Supported",
            },
            {
                "sentence": "The experiment succeeded.",
                "y_true": 0,
                "y_pred": 0,
                "task_type": "Summary",
                "confidence": 0.95,
                "source_snippet": "Context",
                "ground_truth_label": "Supported",
            },
        ],
    }

    results_file = tmp_path / "benchmark.json"
    with open(results_file, "w", encoding="utf-8") as f:
        json.dump(benchmark_dict, f)

    analyzer = ErrorAnalyzer.from_benchmark_results(results_file)
    assert len(analyzer.records) == 2

    md_path = tmp_path / "FAILURE_ANALYSIS.md"
    json_path = tmp_path / "failure_analysis.json"
    analysis = analyzer.save_report(markdown_path=str(md_path), json_path=str(json_path))

    assert md_path.exists()
    assert json_path.exists()

    with open(md_path, "r", encoding="utf-8") as f:
        content = f.read()
    assert "Hearsay Evaluation: Error Analysis & Failure Mode Taxonomy" in content
    assert "Confusion Matrix" in content
