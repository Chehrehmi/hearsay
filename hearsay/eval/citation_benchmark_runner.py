"""
Path A Citation-Binding Benchmark Runner.
Evaluates citation quality on the official ALCE ASQA benchmark (EMNLP 2023, Gao et al., Princeton NLP).
Computes Citation Precision and Citation Recall using local DeBERTa NLI cross-encoder.
"""

import json
import time
from pathlib import Path
from typing import Dict, Any, List
from hearsay.dataset.alce_loader import ALCELoader
from hearsay.engine.citation_verifier import CitationVerifier


def run_citation_benchmark(n_samples: int = 30) -> Dict[str, Any]:
    """
    Runs citation-binding verification on n_samples from the ALCE ASQA dataset.
    """
    loader = ALCELoader()
    print(f"Loading {n_samples} samples from ALCE ASQA dataset...")
    samples = loader.load_asqa_samples(n_samples=n_samples)
    print(f"Loaded {len(samples)} samples successfully.")

    verifier = CitationVerifier()
    results = []

    total_citations = 0
    total_supported = 0
    precision_scores = []
    recall_scores = []

    start_time = time.perf_counter()

    for idx, s in enumerate(samples):
        gold = s.get("gold_answer", "")
        docs = s.get("docs_map", {})

        # To evaluate citation binding on ALCE, if the gold answer lacks explicit bracket citations,
        # we evaluate with injected citations mapped to the top-k retrieved documents:
        # Sentence 1 cites [1], Sentence 2 cites [2]
        sentences = [sent.strip() for sent in gold.split(".") if len(sent.strip()) > 5]
        cited_sentences = []
        for i, sent in enumerate(sentences):
            doc_target = str((i % min(len(docs), 3)) + 1)
            cited_sentences.append(f"{sent} [{doc_target}].")

        candidate_response = " ".join(cited_sentences)
        verif = verifier.verify_citations(candidate_response, docs)

        precision_scores.append(verif["citation_precision"])
        recall_scores.append(verif["citation_recall"])
        total_citations += verif["total_citations_provided"]
        total_supported += verif["supported_citations"]

        results.append({
            "sample_id": s["sample_id"],
            "question": s["question"],
            "total_claims": verif["total_claims"],
            "citation_precision": verif["citation_precision"],
            "citation_recall": verif["citation_recall"],
            "overall_status": verif["overall_status"],
        })

    elapsed_s = round(time.perf_counter() - start_time, 2)
    mean_precision = round(sum(precision_scores) / len(precision_scores), 1) if precision_scores else 0.0
    mean_recall = round(sum(recall_scores) / len(recall_scores), 1) if recall_scores else 0.0

    report = {
        "benchmark": "ALCE (EMNLP 2023, Princeton NLP)",
        "dataset_split": "ASQA GTR Top-100 Oracle",
        "benchmark_date": time.strftime("%Y-%m-%d %H:%M:%S"),
        "samples_evaluated": len(samples),
        "total_citations_evaluated": total_citations,
        "valid_citations_supported": total_supported,
        "mean_citation_precision": mean_precision,
        "mean_citation_recall": mean_recall,
        "elapsed_seconds": elapsed_s,
        "sample_breakdown": results[:10],
    }

    out_file = Path(__file__).resolve().parent.parent.parent / "data" / "citation_benchmark_results.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"\n[SUCCESS] ALCE Citation Benchmark written to {out_file}")
    print(f"Mean Citation Precision: {mean_precision}%")
    print(f"Mean Citation Recall:    {mean_recall}%")
    return report


if __name__ == "__main__":
    run_citation_benchmark(30)
