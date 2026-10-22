from typing import Dict, List, Any
from sklearn.metrics import precision_score, recall_score, f1_score, accuracy_score


def compute_groundedness_metrics(y_true: List[int], y_pred: List[int]) -> Dict[str, float]:
    """Computes binary classification metrics for hallucination detection.

    Convention:
        1 = Unsupported / Hallucination
        0 = Supported / Grounded

    Args:
        y_true: Ground-truth binary labels.
        y_pred: Predicted binary labels.

    Returns:
        Dict containing precision, recall, f1, and accuracy rounded to 4 decimal places.
    """
    if not y_true or not y_pred or len(y_true) != len(y_pred):
        return {
            "precision": 0.0,
            "recall": 0.0,
            "f1": 0.0,
            "accuracy": 0.0,
        }

    return {
        "precision": round(float(precision_score(y_true, y_pred, zero_division=0)), 4),
        "recall": round(float(recall_score(y_true, y_pred, zero_division=0)), 4),
        "f1": round(float(f1_score(y_true, y_pred, zero_division=0)), 4),
        "accuracy": round(float(accuracy_score(y_true, y_pred)), 4),
    }


def compute_per_task_metrics(eval_records: List[Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
    """Computes groundedness metrics broken down by task_type (e.g., QA, Summarization, Data-to-Text).

    Args:
        eval_records: List of record dicts containing 'task_type', 'y_true', and 'y_pred'.

    Returns:
        Dict mapping task_type to its computed metrics dict.
    """
    task_groups: Dict[str, Dict[str, List[int]]] = {}

    for rec in eval_records:
        task = rec.get("task_type", "Unknown")
        if task not in task_groups:
            task_groups[task] = {"y_true": [], "y_pred": []}
        task_groups[task]["y_true"].append(rec["y_true"])
        task_groups[task]["y_pred"].append(rec["y_pred"])

    results = {}
    for task, data in task_groups.items():
        results[task] = compute_groundedness_metrics(data["y_true"], data["y_pred"])

    return results
