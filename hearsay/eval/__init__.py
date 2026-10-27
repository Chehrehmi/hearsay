# Hearsay Evaluation & Benchmarking
from hearsay.eval.aligner import RAGTruthAligner
from hearsay.eval.benchmark_runner import (
    MockEngine,
    compute_latency_profile,
    generate_markdown_summary,
    run_benchmark,
)
from hearsay.eval.error_analysis import (
    ALL_TAXONOMY_CATEGORIES,
    TAXONOMY_ENTITY_NUMERIC,
    TAXONOMY_OTHER,
    TAXONOMY_SPAN_MISALIGNMENT,
    TAXONOMY_SUBTLE_NUANCE,
    TAXONOMY_UNRETRIEVED_CONTEXT,
    TAXONOMY_WORLD_KNOWLEDGE,
    ErrorAnalyzer,
)
from hearsay.eval.metrics import compute_groundedness_metrics, compute_per_task_metrics
from hearsay.eval.report_generator import (
    EvaluationReportGenerator,
    generate_ascii_bar,
    generate_evaluation_report,
)

__all__ = [
    "RAGTruthAligner",
    "compute_groundedness_metrics",
    "compute_per_task_metrics",
    "run_benchmark",
    "MockEngine",
    "compute_latency_profile",
    "generate_markdown_summary",
    "ErrorAnalyzer",
    "ALL_TAXONOMY_CATEGORIES",
    "TAXONOMY_SPAN_MISALIGNMENT",
    "TAXONOMY_SUBTLE_NUANCE",
    "TAXONOMY_ENTITY_NUMERIC",
    "TAXONOMY_UNRETRIEVED_CONTEXT",
    "TAXONOMY_WORLD_KNOWLEDGE",
    "TAXONOMY_OTHER",
    "EvaluationReportGenerator",
    "generate_evaluation_report",
    "generate_ascii_bar",
]
