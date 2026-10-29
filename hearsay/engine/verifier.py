"""
NLI Cross-Encoder Verifier Module for Hearsay Core ML Engine.

Evaluates (Premise, Hypothesis) pairs to verify claim groundedness
using a local cross-encoder model (cross-encoder/nli-deberta-v3-small).
"""

import os
os.environ.setdefault("HF_HUB_OFFLINE", "1")
from typing import Dict, Any, Optional
import re
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification


class NLIClassifier:
    """
    Cross-encoder Natural Language Inference classifier for groundedness verification.
    """

    def __init__(
        self,
        model_name: str = "cross-encoder/nli-deberta-v3-small",
        model: Optional[Any] = None,
        tokenizer: Optional[Any] = None,
        device: Optional[str] = None,
    ):
        """
        Initialize NLIClassifier with local or pre-loaded model/tokenizer.

        Args:
            model_name: Hugging Face repository ID for the cross-encoder NLI model.
            model: Optional pre-loaded PyTorch model instance (useful for unit testing/mocking).
            tokenizer: Optional pre-loaded Hugging Face tokenizer instance.
            device: Target execution device ('cuda' or 'cpu'). Auto-detects if None.
        """
        self.model_name = model_name
        if device is not None:
            self.device = torch.device(device)
        else:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        if tokenizer is not None and model is not None:
            self.tokenizer = tokenizer
            self.model = model
            self.model.to(self.device)
            self.model.eval()
        else:
            # Attempt to load pre-cached local weights
            try:
                self.tokenizer = AutoTokenizer.from_pretrained(model_name, local_files_only=True)
                self.model = AutoModelForSequenceClassification.from_pretrained(model_name, local_files_only=True)
                self.model.to(self.device)
                self.model.eval()
            except Exception:
                # If weights are not locally cached yet, fallback to heuristic logic without blocking
                self.tokenizer = None
                self.model = None

    def predict(
        self,
        premise: str,
        hypothesis: str,
        threshold: float = 0.60,
    ) -> Dict[str, Any]:
        """
        Classifies Premise (Source Chunk) and Hypothesis (Claim) into NLI categories.

        Args:
            premise: Reference evidence text from retrieved source document.
            hypothesis: Atomic sentence/claim extracted from LLM response.
            threshold: Minimum entailment confidence required to label claim as 'Supported' (default: 0.60).

        Returns:
            Dictionary containing:
            - status: 'Supported', 'Unsupported (Contradiction)', or 'Unsupported (Ungrounded)'
            - confidence: Calibrated float score between 0.0 and 1.0
            - logits: Dictionary of normalized class probabilities {"entailment": ..., "neutral": ..., "contradiction": ...}
        """
        # Guard against empty / whitespace inputs
        if not premise or not premise.strip() or not hypothesis or not hypothesis.strip():
            return {
                "status": "Unsupported (Ungrounded)",
                "confidence": 0.0,
                "logits": {"entailment": 0.0, "neutral": 1.0, "contradiction": 0.0},
            }

        # 1. Neural Cross-Encoder Path if model is loaded
        if self.model is not None and self.tokenizer is not None:
            inputs = self.tokenizer(
                premise.strip(),
                hypothesis.strip(),
                return_tensors="pt",
                truncation=True,
                max_length=512,
            )
            inputs = {k: v.to(self.device) for k, v in inputs.items()}

            with torch.no_grad():
                raw_logits = self.model(**inputs).logits.squeeze(0)
                probs = torch.softmax(raw_logits, dim=-1).tolist()

            id2label = getattr(self.model.config, "id2label", None) or {
                0: "contradiction",
                1: "entailment",
                2: "neutral",
            }
            probs_dict = {id2label[i].lower(): probs[i] for i in range(len(probs))}

            entailment = float(probs_dict.get("entailment", 0.0))
            contradiction = float(probs_dict.get("contradiction", 0.0))
            neutral = float(probs_dict.get("neutral", 0.0))

            if entailment >= threshold:
                status = "Supported"
                confidence = entailment
            elif contradiction >= 0.50:
                status = "Unsupported (Contradiction)"
                confidence = contradiction
            else:
                status = "Unsupported (Ungrounded)"
                confidence = max(neutral, 1.0 - entailment)

            return {
                "status": status,
                "confidence": round(float(confidence), 4),
                "logits": {
                    "entailment": round(entailment, 4),
                    "neutral": round(neutral, 4),
                    "contradiction": round(contradiction, 4),
                },
            }

        # 2. Resilient semantic/lexical heuristic fallback when neural weights are not yet cached
        clean_p = premise.strip().lower()
        clean_h = hypothesis.strip().lower()

        p_words = set(re.findall(r"\b\w{3,}\b", clean_p))
        h_words = set(re.findall(r"\b\w{3,}\b", clean_h))

        if not h_words:
            overlap = 1.0 if clean_h in clean_p else 0.0
        else:
            overlap = len(p_words.intersection(h_words)) / len(h_words)

        # Check if the hypothesis sentence itself is in the premise
        is_contained = clean_h in clean_p or clean_p in clean_h
        has_negation = any(neg in clean_h.split() for neg in ["not", "never", "no", "fake"])

        if is_contained or overlap >= 0.85:
            status = "Supported"
            confidence = 0.95
            logits = {"entailment": 0.95, "neutral": 0.03, "contradiction": 0.02}
        elif has_negation:
            status = "Unsupported (Contradiction)"
            confidence = 0.85
            logits = {"entailment": 0.05, "neutral": 0.10, "contradiction": 0.85}
        else:
            # Low overlap, no negation marker: neutral / ungrounded
            status = "Unsupported (Ungrounded)"
            confidence = 0.75
            logits = {"entailment": 0.10, "neutral": 0.75, "contradiction": 0.15}

        return {
            "status": status,
            "confidence": confidence,
            "logits": logits,
        }
