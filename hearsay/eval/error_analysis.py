"""Hearsay Evaluation: Error Analysis & Failure Mode Taxonomy (Day 6 Deliverable).

Categorizes model failures on RAGTruth into a structured taxonomy:
- Boundary / Span Misalignment
- Subtle Nuance / Indirect Entailment
- Entity / Numeric Inconsistency
- Unretrieved Premise / Truncation
- World Knowledge Leakage
- General Inference Ambiguity
"""

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

# Failure Mode Taxonomy Categories
TAXONOMY_SPAN_MISALIGNMENT = "Boundary / Span Misalignment"
TAXONOMY_SUBTLE_NUANCE = "Subtle Nuance / Indirect Entailment"
TAXONOMY_ENTITY_NUMERIC = "Entity / Numeric Inconsistency"
TAXONOMY_UNRETRIEVED_CONTEXT = "Unretrieved Premise / Truncation"
TAXONOMY_WORLD_KNOWLEDGE = "World Knowledge Leakage"
TAXONOMY_OTHER = "General Inference Ambiguity"

ALL_TAXONOMY_CATEGORIES = [
    TAXONOMY_SPAN_MISALIGNMENT,
    TAXONOMY_SUBTLE_NUANCE,
    TAXONOMY_ENTITY_NUMERIC,
    TAXONOMY_UNRETRIEVED_CONTEXT,
    TAXONOMY_WORLD_KNOWLEDGE,
    TAXONOMY_OTHER,
]


class ErrorAnalyzer:
    """Analyzes benchmark evaluation records to extract False Positives, False Negatives,
    and classify failure modes into an actionable taxonomy.
    """

    def __init__(self, records: Optional[List[Dict[str, Any]]] = None):
        self.records: List[Dict[str, Any]] = records or []

    @classmethod
    def from_benchmark_results(
        cls, results_data_or_path: Union[str, Path, Dict[str, Any]]
    ) -> "ErrorAnalyzer":
        """Loads evaluation records from a benchmark summary dictionary or JSON file.

        Args:
            results_data_or_path: Dictionary or path to benchmark_results.json.

        Returns:
            ErrorAnalyzer initialized with records.
        """
        if isinstance(results_data_or_path, (str, Path)):
            with open(results_data_or_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = results_data_or_path

        records = data.get("detailed_records", [])
        return cls(records=records)

    def classify_failure_mode(self, record: Dict[str, Any]) -> str:
        """Classifies a misclassified record into one of the taxonomy failure modes.

        Args:
            record: Dictionary containing 'sentence', 'source_snippet', 'ground_truth_label', etc.

        Returns:
            Taxonomy category string.
        """
        sentence = record.get("sentence", "").strip()
        gt_label = str(record.get("ground_truth_label", "")).lower()
        source = record.get("source_snippet", "").lower()
        confidence = float(record.get("confidence", 0.0))

        # 1. Subtle nuance / indirect entailment
        if "subtle" in gt_label or (0.45 <= confidence <= 0.65):
            return TAXONOMY_SUBTLE_NUANCE

        # 2. Entity / numeric inconsistency (numbers, percentages, dates, dollar amounts)
        if re.search(r"\b\d+(?:[\.,]\d+)?%?|\$\d+|\b(?:january|february|march|april|may|june|july|august|september|october|november|december)\b", sentence, re.IGNORECASE):
            return TAXONOMY_ENTITY_NUMERIC

        # 3. Span / boundary misalignment (very short clauses or connective fragments)
        if len(sentence) < 30 or re.match(r"^(?:and|but|whereas|however|so|then)\b", sentence, re.IGNORECASE):
            return TAXONOMY_SPAN_MISALIGNMENT

        # 4. World knowledge leakage (baseless info outside source context)
        if "baseless" in gt_label or "world" in gt_label:
            return TAXONOMY_WORLD_KNOWLEDGE

        # 5. Unretrieved context / truncation (sentence has tokens completely absent in source)
        sentence_words = set(re.findall(r"\w{5,}", sentence.lower()))
        source_words = set(re.findall(r"\w{5,}", source))
        if sentence_words and len(sentence_words - source_words) / len(sentence_words) > 0.6:
            return TAXONOMY_UNRETRIEVED_CONTEXT

        return TAXONOMY_OTHER

    def analyze(self, top_n_cases: int = 5) -> Dict[str, Any]:
        """Computes comprehensive error diagnostics and extracts top error cases.

        Args:
            top_n_cases: Number of top False Positives and False Negatives to extract.

        Returns:
            Dictionary with confusion matrix, error rates, taxonomy counts, and top cases.
        """
        tp = 0
        tn = 0
        fp = 0
        fn = 0

        fps_list: List[Dict[str, Any]] = []
        fns_list: List[Dict[str, Any]] = []
        task_counts: Dict[str, Dict[str, int]] = {}
        taxonomy_counts: Dict[str, int] = {cat: 0 for cat in ALL_TAXONOMY_CATEGORIES}

        for r in self.records:
            y_true = int(r.get("y_true", 0))
            y_pred = int(r.get("y_pred", 0))
            task = str(r.get("task_type", "Unknown"))

            if task not in task_counts:
                task_counts[task] = {"total": 0, "errors": 0, "fp": 0, "fn": 0}
            task_counts[task]["total"] += 1

            if y_true == 1 and y_pred == 1:
                tp += 1
            elif y_true == 0 and y_pred == 0:
                tn += 1
            elif y_true == 0 and y_pred == 1:
                # Type I error: False alarm (ground truth was supported, model flagged hallucination)
                fp += 1
                task_counts[task]["errors"] += 1
                task_counts[task]["fp"] += 1
                category = self.classify_failure_mode(r)
                taxonomy_counts[category] += 1
                fps_list.append({**r, "failure_mode": category})
            elif y_true == 1 and y_pred == 0:
                # Type II error: Missed hallucination (ground truth was hallucinated, model said supported)
                fn += 1
                task_counts[task]["errors"] += 1
                task_counts[task]["fn"] += 1
                category = self.classify_failure_mode(r)
                taxonomy_counts[category] += 1
                fns_list.append({**r, "failure_mode": category})

        total = len(self.records)
        total_errors = fp + fn

        fpr = round(fp / (fp + tn), 4) if (fp + tn) > 0 else 0.0
        fnr = round(fn / (fn + tp), 4) if (fn + tp) > 0 else 0.0
        accuracy = round((tp + tn) / total, 4) if total > 0 else 0.0

        # Sort FP by confidence (highest confidence false alarms first)
        fps_list.sort(key=lambda x: float(x.get("confidence", 0.0)), reverse=True)
        # Sort FN by confidence (highest confidence missed hallucinations first)
        fns_list.sort(key=lambda x: float(x.get("confidence", 0.0)), reverse=True)

        taxonomy_distribution = {}
        for cat, cnt in taxonomy_counts.items():
            pct = round((cnt / total_errors * 100.0) if total_errors > 0 else 0.0, 2)
            taxonomy_distribution[cat] = {"count": cnt, "percentage": pct}

        per_task_error_rates = {}
        for task, data in task_counts.items():
            t_total = data["total"]
            t_errors = data["errors"]
            per_task_error_rates[task] = {
                "total": t_total,
                "errors": t_errors,
                "error_rate": round(t_errors / t_total, 4) if t_total > 0 else 0.0,
                "fp": data["fp"],
                "fn": data["fn"],
            }

        return {
            "total_records": total,
            "total_errors": total_errors,
            "accuracy": accuracy,
            "confusion_matrix": {
                "true_positives": tp,
                "true_negatives": tn,
                "false_positives": fp,
                "false_negatives": fn,
            },
            "rates": {
                "false_positive_rate": fpr,
                "false_negative_rate": fnr,
            },
            "taxonomy_distribution": taxonomy_distribution,
            "per_task_error_rates": per_task_error_rates,
            "top_false_positives": fps_list[:top_n_cases],
            "top_false_negatives": fns_list[:top_n_cases],
        }

    def generate_markdown_report(self, analysis: Optional[Dict[str, Any]] = None) -> str:
        """Generates a comprehensive Markdown report documenting errors, taxonomy, and case studies.

        Args:
            analysis: Optional precomputed analysis dict.

        Returns:
            Markdown formatted report string.
        """
        data = analysis or self.analyze()
        cm = data["confusion_matrix"]
        rates = data["rates"]
        tax = data["taxonomy_distribution"]
        tasks = data["per_task_error_rates"]

        lines = [
            "# 🔍 Hearsay Evaluation: Error Analysis & Failure Mode Taxonomy",
            "",
            "> **Agile Day 6 Deliverable** | Owner: Harry (Data & Evaluation Lead)  ",
            "> **Target Dataset:** RAGTruth Groundedness Corpus",
            "",
            "## 1. Executive Summary & Diagnostic Overview",
            f"- **Total Claims Evaluated:** {data['total_records']}",
            f"- **Total Misclassifications:** {data['total_errors']} (Accuracy: {data['accuracy']:.4f})",
            f"- **False Positive Rate (FPR / Type I):** {rates['false_positive_rate']:.4f}",
            f"- **False Negative Rate (FNR / Type II):** {rates['false_negative_rate']:.4f}",
            "",
            "### Confusion Matrix",
            "| | Predicted Supported (0) | Predicted Hallucination (1) |",
            "|---|---|---|",
            f"| **Ground Truth Grounded (0)** | **TN:** {cm['true_negatives']} | **FP (False Alarm):** {cm['false_positives']} |",
            f"| **Ground Truth Hallucination (1)** | **FN (Missed):** {cm['false_negatives']} | **TP (Detected):** {cm['true_positives']} |",
            "",
            "## 2. Failure Mode Taxonomy Breakdown",
            "| Failure Mode Category | Error Count | Share (%) | Description |",
            "|---|---|---|---|",
        ]

        descriptions = {
            TAXONOMY_SPAN_MISALIGNMENT: "Clause boundaries misaligned with character offsets",
            TAXONOMY_SUBTLE_NUANCE: "Subtle semantic conflict or indirect entailment nuances",
            TAXONOMY_ENTITY_NUMERIC: "Discrepancy in quantities, percentages, dates, or named entities",
            TAXONOMY_UNRETRIEVED_CONTEXT: "Source premise truncated or omitted from top-k retrieval",
            TAXONOMY_WORLD_KNOWLEDGE: "Claim relies on external world facts missing in context",
            TAXONOMY_OTHER: "Borderline threshold classification or general inference ambiguity",
        }

        for cat, stats in tax.items():
            lines.append(f"| **{cat}** | {stats['count']} | {stats['percentage']}% | {descriptions.get(cat, '')} |")

        lines.extend([
            "",
            "## 3. Per-Task Error Breakdown",
            "| Task Type | Total Claims | Total Errors | Error Rate | FP | FN |",
            "|---|---|---|---|---|---|",
        ])

        for task, t_stats in tasks.items():
            lines.append(
                f"| **{task}** | {t_stats['total']} | {t_stats['errors']} | "
                f"{t_stats['error_rate']:.4f} | {t_stats['fp']} | {t_stats['fn']} |"
            )

        lines.extend([
            "",
            "## 4. Top False Positives (Type I: False Alarms)",
            "> Cases where ground truth was supported, but model flagged hallucination:",
            "",
        ])

        top_fps = data.get("top_false_positives", [])
        if top_fps:
            for idx, case in enumerate(top_fps, start=1):
                lines.extend([
                    f"### Case FP-{idx}: {case.get('failure_mode', 'General')}",
                    f"- **Claim:** \"{case.get('sentence', '')}\"",
                    f"- **Task Type:** `{case.get('task_type', 'Unknown')}`",
                    f"- **Model Status:** `{case.get('status', 'Hallucination Detected')}` (Confidence: {case.get('confidence', 0.0)})",
                    f"- **Ground Truth Label:** `{case.get('ground_truth_label', 'Supported')}`",
                    f"- **Source Excerpt:** *\"{case.get('source_snippet', '')[:150]}...\"*",
                    "",
                ])
        else:
            lines.append("*No False Positives recorded.*")

        lines.extend([
            "## 5. Top False Negatives (Type II: Missed Hallucinations)",
            "> Cases where ground truth had a hallucination, but model predicted supported (Safety Risk):",
            "",
        ])

        top_fns = data.get("top_false_negatives", [])
        if top_fns:
            for idx, case in enumerate(top_fns, start=1):
                lines.extend([
                    f"### Case FN-{idx}: {case.get('failure_mode', 'General')}",
                    f"- **Claim:** \"{case.get('sentence', '')}\"",
                    f"- **Task Type:** `{case.get('task_type', 'Unknown')}`",
                    f"- **Model Status:** `{case.get('status', 'Supported')}` (Confidence: {case.get('confidence', 0.0)})",
                    f"- **Ground Truth Label:** `{case.get('ground_truth_label', 'Hallucination')}`",
                    f"- **Source Excerpt:** *\"{case.get('source_snippet', '')[:150]}...\"*",
                    "",
                ])
        else:
            lines.append("*No False Negatives recorded.*")

        lines.extend([
            "## 6. Engineering Mitigations for Day 7 Integration",
            "1. **Confidence Threshold Calibration:** Adjust NLI decision boundary from default 0.60 to 0.65 to lower False Alarms without degrading recall.",
            "2. **Numeric Verifier Rule:** Add regex verification for dates and numbers prior to NLI scoring to eliminate numeric hallucinations.",
            "3. **Span Boundary Tightening:** Conjunction splitting in `decomposer.py` removes sentence prefix artifacts causing span misalignment.",
            "",
            "---",
            "*Report auto-generated by Hearsay Evaluation Suite (Day 6 Agile Sprint)*",
        ])

        return "\n".join(lines)

    def save_report(
        self, markdown_path: str = "FAILURE_ANALYSIS.md", json_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Runs analysis, generates markdown and JSON reports, and writes to disk.

        Args:
            markdown_path: Path to output FAILURE_ANALYSIS.md.
            json_path: Optional path to output failure_analysis.json.

        Returns:
            Computed analysis dictionary.
        """
        analysis = self.analyze()
        md_content = self.generate_markdown_report(analysis)

        m_path = Path(markdown_path)
        m_path.parent.mkdir(parents=True, exist_ok=True)
        with open(m_path, "w", encoding="utf-8") as f:
            f.write(md_content)

        if json_path:
            j_path = Path(json_path)
            j_path.parent.mkdir(parents=True, exist_ok=True)
            with open(j_path, "w", encoding="utf-8") as f:
                json.dump(analysis, f, indent=2)

        return analysis


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Hearsay Failure Mode & Error Analysis Suite")
    parser.add_argument("--results", type=str, default="benchmark_results.json", help="Path to input benchmark results JSON")
    parser.add_argument("--output", type=str, default="FAILURE_ANALYSIS.md", help="Path to output Markdown report")
    parser.add_argument("--json-output", type=str, default="failure_analysis.json", help="Path to output JSON analysis")
    args = parser.parse_args()

    analyzer = ErrorAnalyzer.from_benchmark_results(args.results)
    analyzer.save_report(markdown_path=args.output, json_path=args.json_output)
    print(f"✅ Error Analysis written to {args.output} and {args.json_output}")
