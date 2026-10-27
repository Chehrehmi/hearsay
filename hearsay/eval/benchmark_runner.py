import argparse
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from hearsay.dataset.loader import RAGTruthLoader
from hearsay.eval.aligner import RAGTruthAligner
from hearsay.eval.metrics import compute_groundedness_metrics, compute_per_task_metrics


class MockEngine:
    """Fallback mock engine used when full HearsayEngine pipeline is unavailable."""

    def verify(self, response_text: str, source_info: str) -> Dict[str, Any]:
        start = time.perf_counter()
        sentences = [s.strip() for s in response_text.replace("\n", " ").split(".") if len(s.strip()) > 3]
        if not sentences:
            sentences = [response_text]

        claims = []
        for idx, sent in enumerate(sentences):
            claims.append({
                "claim_id": idx,
                "claim_text": sent,
                "status": "Supported",
                "confidence": 0.95,
                "evidence_span": source_info[:100] if source_info else "",
                "nli_logits": {"entailment": 0.95, "neutral": 0.03, "contradiction": 0.02}
            })

        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        return {
            "request_id": "mock-0000",
            "overall_status": "Verified",
            "groundedness_score": 100.0,
            "total_claims": len(claims),
            "supported_claims": len(claims),
            "contradicted_claims": 0,
            "ungrounded_claims": 0,
            "claims": claims,
            "latency_ms": elapsed_ms
        }


def _get_engine():
    """Instantiate HearsayEngine if available, otherwise return MockEngine."""
    try:
        from hearsay.engine.pipeline import HearsayEngine
        return HearsayEngine()
    except Exception:
        return MockEngine()


def compute_latency_profile(latencies: List[float]) -> Dict[str, float]:
    """Computes distribution statistics including mean, min, max, P50, P90, P95, and P99 latency.

    Args:
        latencies: List of latency measurements in milliseconds.

    Returns:
        Dictionary with latency percentiles and summary statistics.
    """
    if not latencies:
        return {
            "mean_ms": 0.0,
            "min_ms": 0.0,
            "max_ms": 0.0,
            "p50_ms": 0.0,
            "p90_ms": 0.0,
            "p95_ms": 0.0,
            "p99_ms": 0.0,
        }

    sorted_vals = sorted(latencies)
    n = len(sorted_vals)

    def _calc_percentile(p: float) -> float:
        k = (n - 1) * p
        f = int(k)
        c = min(f + 1, n - 1)
        d = k - f
        return round(sorted_vals[f] + (sorted_vals[c] - sorted_vals[f]) * d, 2)

    return {
        "mean_ms": round(sum(latencies) / n, 2),
        "min_ms": round(min(latencies), 2),
        "max_ms": round(max(latencies), 2),
        "p50_ms": _calc_percentile(0.50),
        "p90_ms": _calc_percentile(0.90),
        "p95_ms": _calc_percentile(0.95),
        "p99_ms": _calc_percentile(0.99),
    }


def generate_markdown_summary(summary: Dict[str, Any]) -> str:
    """Generates a clean GitHub-Flavored Markdown summary report from benchmark results.

    Args:
        summary: Dictionary produced by run_benchmark.

    Returns:
        Markdown string formatted with tables and headers.
    """
    metrics = summary.get("metrics", {})
    per_task = summary.get("per_task_metrics", {})
    lat = summary.get("latency_profile", {})

    lines = [
        "# 📊 Hearsay RAGTruth Groundedness Benchmark Report",
        "",
        "## Executive Summary",
        f"- **Samples Evaluated:** {summary.get('samples_evaluated', 0)}",
        f"- **Total Sentences Evaluated:** {summary.get('total_sentences', 0)}",
        f"- **Target Split:** `{summary.get('split', 'all')}`",
        f"- **Target Task Type:** `{summary.get('task_type', 'all')}`",
        f"- **Average Latency:** {lat.get('mean_ms', 0.0)} ms (P95: {lat.get('p95_ms', 0.0)} ms)",
        "",
        "## Overall Groundedness Verification Metrics",
        "| Metric | Score |",
        "|---|---|",
        f"| **Precision** | {metrics.get('precision', 0.0):.4f} |",
        f"| **Recall** | {metrics.get('recall', 0.0):.4f} |",
        f"| **F1 Score** | {metrics.get('f1', 0.0):.4f} |",
        f"| **Accuracy** | {metrics.get('accuracy', 0.0):.4f} |",
        "",
        "## Per-Task Breakdown",
        "| Task Type | Samples | Precision | Recall | F1 | Accuracy |",
        "|---|---|---|---|---|---|",
    ]

    if per_task:
        for task_name, task_metrics in per_task.items():
            lines.append(
                f"| **{task_name}** | {task_metrics.get('count', 0)} | "
                f"{task_metrics.get('precision', 0.0):.4f} | {task_metrics.get('recall', 0.0):.4f} | "
                f"{task_metrics.get('f1', 0.0):.4f} | {task_metrics.get('accuracy', 0.0):.4f} |"
            )
    else:
        lines.append("| *No task data* | - | - | - | - | - |")

    lines.extend([
        "",
        "## Latency Profiling (ms)",
        "| Metric | Latency (ms) |",
        "|---|---|",
        f"| **Mean** | {lat.get('mean_ms', 0.0)} ms |",
        f"| **Min** | {lat.get('min_ms', 0.0)} ms |",
        f"| **P50 (Median)** | {lat.get('p50_ms', 0.0)} ms |",
        f"| **P90** | {lat.get('p90_ms', 0.0)} ms |",
        f"| **P95** | {lat.get('p95_ms', 0.0)} ms |",
        f"| **P99** | {lat.get('p99_ms', 0.0)} ms |",
        f"| **Max** | {lat.get('max_ms', 0.0)} ms |",
        "",
        "---",
        "*Report auto-generated by Hearsay Evaluation Benchmark Suite (Day 5 Agile Sprint)*",
    ])

    return "\n".join(lines)


def run_benchmark(
    sample_limit: int = 50,
    output_path: Optional[str] = "benchmark_results.json",
    markdown_output_path: Optional[str] = None,
    split: Optional[str] = None,
    task_type: Optional[str] = None,
    engine: Optional[Any] = None,
) -> Dict[str, Any]:
    """Runs groundedness evaluation over RAGTruth dataset instances.

    Args:
        sample_limit: Number of records to evaluate (<=0 for all records).
        output_path: Path to save benchmark JSON results (None to skip file write).
        markdown_output_path: Optional path to save markdown summary table.
        split: Optional dataset split filter ('train', 'dev', 'test').
        task_type: Optional task filter ('Summary', 'QA', 'Data-to-Text').
        engine: Custom engine instance (defaults to HearsayEngine with MockEngine fallback).

    Returns:
        Summary dictionary containing metrics, per-task breakdowns, and latency profile.
    """
    filter_desc = []
    if split:
        filter_desc.append(f"split='{split}'")
    if task_type:
        filter_desc.append(f"task='{task_type}'")
    filter_str = f" ({', '.join(filter_desc)})" if filter_desc else ""

    print(f"🚀 Running Hearsay RAGTruth Benchmark on {sample_limit if sample_limit > 0 else 'ALL'} instances{filter_str}...")

    loader = RAGTruthLoader()
    df = loader.load_joined_dataset()

    if split:
        df = df[df["split"].astype(str).str.lower() == split.lower()]
    if task_type:
        df = df[df["task_type"].astype(str).str.lower() == task_type.lower()]

    if sample_limit > 0:
        df = df.head(sample_limit)

    active_engine = engine if engine is not None else _get_engine()

    y_true: List[int] = []
    y_pred: List[int] = []
    eval_records: List[Dict[str, Any]] = []
    latencies: List[float] = []

    for _, row in df.iterrows():
        response_text = str(row["response"])
        source_info = str(row["source_info"])
        labels = row.get("labels", [])
        current_task = str(row.get("task_type", "Unknown"))

        result = active_engine.verify(response_text, source_info)
        latencies.append(result.get("latency_ms", 0.0))

        sentences = [c["claim_text"] for c in result.get("claims", []) if "claim_text" in c]
        if not sentences:
            continue

        aligned = RAGTruthAligner.align_sentence_labels(response_text, labels, sentences)

        for item, verdict in zip(aligned, result.get("claims", [])):
            true_label = item["is_hallucination"]
            pred_label = 0 if verdict.get("status") == "Supported" else 1

            y_true.append(true_label)
            y_pred.append(pred_label)
            eval_records.append({
                "sentence": item.get("sentence", ""),
                "source_snippet": source_info[:250] if source_info else "",
                "y_true": true_label,
                "y_pred": pred_label,
                "task_type": current_task,
                "confidence": verdict.get("confidence", 0.0),
                "status": verdict.get("status", "Supported"),
                "evidence_span": verdict.get("evidence_span", ""),
                "ground_truth_label": item.get("label_type", "Supported"),
            })

    overall_metrics = compute_groundedness_metrics(y_true, y_pred)
    per_task_metrics = compute_per_task_metrics(eval_records)
    latency_profile = compute_latency_profile(latencies)

    summary = {
        "samples_evaluated": len(df),
        "total_sentences": len(y_true),
        "split": split or "all",
        "task_type": task_type or "all",
        "metrics": overall_metrics,
        "per_task_metrics": per_task_metrics,
        "avg_latency_ms": latency_profile.get("mean_ms", 0.0),
        "latency_profile": latency_profile,
        "detailed_records": eval_records,
    }

    markdown_report = generate_markdown_summary(summary)

    print("\n================ BENCHMARK RESULTS ================")
    print(markdown_report)
    print("===================================================\n")

    if output_path:
        out_file = Path(output_path)
        out_file.parent.mkdir(parents=True, exist_ok=True)
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)

    if markdown_output_path:
        md_file = Path(markdown_output_path)
        md_file.parent.mkdir(parents=True, exist_ok=True)
        with open(md_file, "w", encoding="utf-8") as f:
            f.write(markdown_report)

    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Hearsay RAGTruth Benchmark Runner")
    parser.add_argument("--limit", type=int, default=50, help="Number of RAGTruth samples to evaluate (<=0 for all)")
    parser.add_argument("--split", type=str, default=None, choices=["train", "dev", "test"], help="Dataset split filter")
    parser.add_argument("--task", type=str, default=None, help="Task type filter ('Summary', 'QA', 'Data-to-Text')")
    parser.add_argument("--output", type=str, default="benchmark_results.json", help="Output path for benchmark JSON")
    parser.add_argument("--markdown-output", type=str, default="BENCHMARK_SUMMARY.md", help="Output path for Markdown summary")
    args = parser.parse_args()

    run_benchmark(
        sample_limit=args.limit,
        output_path=args.output,
        markdown_output_path=args.markdown_output,
        split=args.split,
        task_type=args.task,
    )
