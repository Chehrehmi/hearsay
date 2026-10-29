"""
Empirical Adversarial Robustness Evaluator for Hearsay NLI Verification Engine.

Benchmarked on RAGTruth (ACL 2024, Niu et al.).
Evaluates detector degradation (Evasion Success Rate - ESR) under 3 linguistic perturbation vectors:
1. Lexical Synonym Substitution (TextAttack WordSwapWordNet / Morris et al., EMNLP 2020)
2. Epistemic Hedging Injection (CoNLL-2010 Hedge Detection Taxonomy / Hyland, 1998)
3. Syntactic Inversion (CheckList INV / Ribeiro et al., ACL 2020)
"""

import os
import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional

# Ensure offline huggingface cache and NLTK paths are configured
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["MPLCONFIGDIR"] = "/tmp/mpl"
workspace_nltk = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "nltk_data"))
os.environ["NLTK_DATA"] = workspace_nltk

from hearsay.dataset.loader import RAGTruthLoader
from hearsay.engine.pipeline import HearsayEngine
from hearsay.eval.adversarial_attacks import apply_adversarial_attack


def load_ragtruth_hallucinations(data_dir: Path, max_samples: int = 50) -> List[Dict[str, Any]]:
    """
    Extracts real human-annotated factual hallucinations from the RAGTruth ACL 2024 dataset.
    """
    loader = RAGTruthLoader(data_dir=data_dir)
    data = loader.load()
    samples = []

    for item in data:
        if not item.get("labels"):
            continue
        response_text = item.get("response", "")
        source_info = item.get("source_info", "")
        task_type = item.get("task_type", "QA")

        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', response_text) if len(s.strip()) > 10]

        for label in item["labels"]:
            ltype = label.get("label_type", "")
            if ltype in ("Evident Conflict", "Evident Baseless Info"):
                span_text = label.get("text", "").strip()
                matched_sentence = None
                for sent in sentences:
                    if span_text in sent:
                        matched_sentence = sent
                        break
                if not matched_sentence:
                    matched_sentence = span_text

                if len(matched_sentence) > 10 and len(source_info) > 15:
                    samples.append({
                        "id": item["id"],
                        "task_type": task_type,
                        "label_type": ltype,
                        "hallucinated_claim": matched_sentence,
                        "span_text": span_text,
                        "source_info": source_info,
                    })
                    if len(samples) >= max_samples:
                        return samples
    return samples


def dehedge_sanitizer(text: str) -> str:
    """
    Hearsay Dual-Path Defense Layer: Verification Sanitizer.
    Strips epistemic modals and hedges before NLI cross-encoder classification.
    """
    cleaned = text.strip()
    hedges = [
        r"^According to available reports,\s*",
        r"^It is widely suggested that\s*",
        r"^Historical sources indicate that\s*",
        r"^It has been asserted that\s*",
        r"^Multiple witnesses suggest that\s*",
        r"^Regarding the record,\s*",
        r"^Historical records document that\s*",
    ]
    for pattern in hedges:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)

    # Capitalize first character
    if cleaned:
        cleaned = cleaned[0].upper() + cleaned[1:]
    return cleaned


import re


def run_robustness_evaluation(
    data_path: Optional[Path] = None,
    output_path: Optional[Path] = None,
    n_samples: int = 50,
) -> Dict[str, Any]:
    """
    Executes the empirical adversarial benchmark across n_samples.
    """
    if data_path is None:
        data_path = Path(__file__).resolve().parent.parent.parent / "data"
    if output_path is None:
        output_path = data_path / "adversarial_results.json"

    print(f"Loading {n_samples} real human-labeled hallucinations from {data_path}...")
    samples = load_ragtruth_hallucinations(data_path, max_samples=n_samples)
    print(f"Loaded {len(samples)} valid hallucinated spans.")

    engine = HearsayEngine()
    attack_types = ["synonym", "hedging", "structural"]

    baseline_detected = 0
    attack_detections = {atk: 0 for atk in attack_types}
    sanitizer_detected = 0

    task_breakdown = {}

    start_time = time.perf_counter()

    for idx, s in enumerate(samples):
        claim = s["hallucinated_claim"]
        source = s["source_info"]
        tt = s["task_type"]

        if tt not in task_breakdown:
            task_breakdown[tt] = {"total": 0, "baseline_caught": 0, "hedged_caught": 0}
        task_breakdown[tt]["total"] += 1

        # 1. Baseline verification on unperturbed hallucination
        res_clean = engine.verify(claim, source)
        clean_caught = res_clean.get("overall_status") != "Verified"
        if clean_caught:
            baseline_detected += 1
            task_breakdown[tt]["baseline_caught"] += 1

        # 2. Perturbation evaluations
        for atk in attack_types:
            perturbed = apply_adversarial_attack(claim, atk)
            res_perturbed = engine.verify(perturbed, source)
            pert_caught = res_perturbed.get("overall_status") != "Verified"
            if pert_caught:
                attack_detections[atk] += 1
                if atk == "hedging":
                    task_breakdown[tt]["hedged_caught"] += 1

        # 3. Dual-Path Defense (Hedge Sanitization)
        hedged = apply_adversarial_attack(claim, "hedging")
        sanitized = dehedge_sanitizer(hedged)
        res_sanitized = engine.verify(sanitized, source)
        if res_sanitized.get("overall_status") != "Verified":
            sanitizer_detected += 1

        if (idx + 1) % 10 == 0 or (idx + 1) == len(samples):
            print(f"Processed {idx + 1}/{len(samples)} samples...")

    elapsed_s = round(time.perf_counter() - start_time, 2)
    total_eval = len(samples)

    bdr = round((baseline_detected / total_eval) * 100.0, 1)

    attacks_report = {}
    for atk in attack_types:
        padr = round((attack_detections[atk] / total_eval) * 100.0, 1)
        # Evasion Success Rate = (BDR - PADR) / BDR
        esr = round(((bdr - padr) / bdr * 100.0), 1) if bdr > 0 else 0.0
        attacks_report[atk] = {
            "post_attack_detection_rate": padr,
            "evasion_success_rate": max(0.0, esr),
            "samples_evaded": max(0, baseline_detected - attack_detections[atk]),
        }

    # Dual-Path Defense Recovery
    defense_padr = round((sanitizer_detected / total_eval) * 100.0, 1)
    defense_robustness = round((sanitizer_detected / baseline_detected * 100.0), 1) if baseline_detected > 0 else 100.0

    task_results = []
    for t_name, t_data in task_breakdown.items():
        t_total = t_data["total"]
        t_base = round((t_data["baseline_caught"] / t_total) * 100.0, 1) if t_total > 0 else 0.0
        t_post = round((t_data["hedged_caught"] / t_total) * 100.0, 1) if t_total > 0 else 0.0
        t_esr = round(((t_base - t_post) / t_base * 100.0), 1) if t_base > 0 else 0.0
        task_results.append({
            "task": t_name,
            "samples_evaluated": t_total,
            "baseline_detection": t_base,
            "post_attack_detection": t_post,
            "evasion_success_rate": max(0.0, t_esr),
        })

    report = {
        "dataset": "RAGTruth ACL 2024",
        "benchmark_date": time.strftime("%Y-%m-%d %H:%M:%S"),
        "samples_evaluated": total_eval,
        "elapsed_seconds": elapsed_s,
        "baseline_detection_rate": bdr,
        "attacks": {
            "synonym_substitution": {
                "vector": "Lexical Invariance (TextAttack WordSwapWordNet)",
                **attacks_report["synonym"],
            },
            "epistemic_hedging": {
                "vector": "Epistemic Modal Injection (CoNLL-2010 Taxonomy)",
                **attacks_report["hedging"],
            },
            "syntactic_paraphrase": {
                "vector": "Syntactic Inversion (CheckList INV)",
                **attacks_report["structural"],
            },
        },
        "hearsay_dual_path_defense": {
            "technique": "Pre-inference Verification Sanitizer (De-hedging)",
            "post_defense_detection_rate": defense_padr,
            "robustness_score": defense_robustness,
        },
        "task_breakdown": task_results,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"\n[SUCCESS] Empirical evaluation written to {output_path}")
    print(json.dumps(report, indent=2))
    return report


if __name__ == "__main__":
    run_robustness_evaluation(n_samples=50)
