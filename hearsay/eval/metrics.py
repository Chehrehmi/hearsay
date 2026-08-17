from typing import List, Dict, Any
from sklearn.metrics import precision_score, recall_score, f1_score, accuracy_score


def compute_groundedness_metrics(y_true: List[int], y_pred: List[int]) -> Dict[str, float]:
  
    if not y_true or not y_pred:
        return {"precision": 0.0, "recall": 0.0, "f1": 0.0, "accuracy": 0.0}

    return {
        "precision": round(float(precision_score(y_true, y_pred, zero_division=0)), 4),
        "recall": round(float(recall_score(y_true, y_pred, zero_division=0)), 4),
        "f1": round(float(f1_score(y_true, y_pred, zero_division=0)), 4),
        "accuracy": round(float(accuracy_score(y_true, y_pred)), 4),
    }


def compute_per_task_metrics(results_by_task: Dict[str, Dict[str, List[int]]]) -> Dict[str, Dict[str, float]]:
   
    task_metrics = {}
    for task_name, data in results_by_task.items():
        task_metrics[task_name] = compute_groundedness_metrics(data["y_true"], data["y_pred"])
    return task_metrics
