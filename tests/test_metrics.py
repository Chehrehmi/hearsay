import pytest
from hearsay.eval.metrics import compute_groundedness_metrics, compute_per_task_metrics
from hearsay.eval import compute_groundedness_metrics as exported_compute_metrics


def test_package_export():
    assert exported_compute_metrics is compute_groundedness_metrics


def test_perfect_predictions():
    y_true = [1, 0, 1, 0, 1]
    y_pred = [1, 0, 1, 0, 1]
    metrics = compute_groundedness_metrics(y_true, y_pred)

    assert metrics["precision"] == 1.0
    assert metrics["recall"] == 1.0
    assert metrics["f1"] == 1.0
    assert metrics["accuracy"] == 1.0


def test_completely_wrong_predictions():
    y_true = [1, 1, 1, 1]
    y_pred = [0, 0, 0, 0]
    metrics = compute_groundedness_metrics(y_true, y_pred)

    assert metrics["precision"] == 0.0
    assert metrics["recall"] == 0.0
    assert metrics["f1"] == 0.0
    assert metrics["accuracy"] == 0.0


def test_partial_predictions():
    # TP=2 (index 0, 2), FP=1 (index 1), FN=1 (index 3), TN=1 (index 4)
    y_true = [1, 0, 1, 1, 0]
    y_pred = [1, 1, 1, 0, 0]
    metrics = compute_groundedness_metrics(y_true, y_pred)

    # Precision = TP / (TP + FP) = 2 / 3 = 0.6667
    # Recall = TP / (TP + FN) = 2 / 3 = 0.6667
    # F1 = 2 * (P * R) / (P + R) = 0.6667
    # Accuracy = (TP + TN) / Total = 3 / 5 = 0.6
    assert metrics["precision"] == 0.6667
    assert metrics["recall"] == 0.6667
    assert metrics["f1"] == 0.6667
    assert metrics["accuracy"] == 0.6


def test_empty_or_mismatched_inputs():
    assert compute_groundedness_metrics([], []) == {
        "precision": 0.0,
        "recall": 0.0,
        "f1": 0.0,
        "accuracy": 0.0,
    }

    assert compute_groundedness_metrics([1, 0], [1]) == {
        "precision": 0.0,
        "recall": 0.0,
        "f1": 0.0,
        "accuracy": 0.0,
    }


def test_zero_division_safety():
    # No positive predictions -> Precision & Recall would divide by zero
    y_true = [0, 0, 0]
    y_pred = [0, 0, 0]
    metrics = compute_groundedness_metrics(y_true, y_pred)

    assert metrics["precision"] == 0.0
    assert metrics["recall"] == 0.0
    assert metrics["f1"] == 0.0
    assert metrics["accuracy"] == 1.0


def test_compute_per_task_metrics():
    eval_records = [
        {"task_type": "QA", "y_true": 1, "y_pred": 1},
        {"task_type": "QA", "y_true": 0, "y_pred": 0},
        {"task_type": "Summarization", "y_true": 1, "y_pred": 0},
        {"task_type": "Summarization", "y_true": 1, "y_pred": 1},
    ]

    results = compute_per_task_metrics(eval_records)
    assert "QA" in results
    assert "Summarization" in results
    assert results["QA"]["accuracy"] == 1.0
    assert results["Summarization"]["recall"] == 0.5
