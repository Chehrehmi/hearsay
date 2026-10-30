"""
HearsayEngine Verification Pipeline Module.

Coordinates the full end-to-end verification pipeline:
1. ClaimDecomposer: Response prose -> Atomic claims
2. BiEncoderRetriever: Source document -> Top candidate evidence spans
3. NLIClassifier: Premise-Hypothesis pairing -> Supported/Contradicted/Ungrounded verdicts
"""

import time
import uuid
import re
from typing import Dict, Any, List, Optional

from hearsay.engine.decomposer import ClaimDecomposer
from hearsay.engine.retriever import BiEncoderRetriever
from hearsay.engine.verifier import NLIClassifier


class HearsayEngine:
    """
    End-to-end groundedness verification engine for RAG pipelines.
    """

    def __init__(
        self,
        decomposer: Optional[ClaimDecomposer] = None,
        retriever: Optional[BiEncoderRetriever] = None,
        verifier: Optional[NLIClassifier] = None,
        confidence_threshold: float = 0.60,
    ):
        """
        Initialize HearsayEngine with pipeline components.
        Allows injecting pre-loaded components for optimal test speed and memory reuse.
        """
        self.decomposer = decomposer if decomposer is not None else ClaimDecomposer()
        self.retriever = retriever if retriever is not None else BiEncoderRetriever()
        self.verifier = verifier if verifier is not None else NLIClassifier()
        self.confidence_threshold = confidence_threshold

    @staticmethod
    def _canonicalize_text(text: str) -> str:
        """
        Linguistic canonicalization for entity grounding:
        Normalizes digit commas, ordinal suffixes, currency/percentage symbols, dotted acronyms, and unicode quotes.
        """
        if not text:
            return ""
        # Unicode quotes and apostrophes to standard ASCII
        t = text.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"').lower()
        # Number formatting (89,500 -> 89500), trailing .0 (15.0 -> 15), and ordinals (15th -> 15)
        t = re.sub(r"(?<=\d),(?=\d)", "", t)
        t = re.sub(r"\b(\d+)\.0\b", r"\1", t)
        t = re.sub(r"\b(\d+)(?:st|nd|rd|th)\b", r"\1", t)
        # Currency and unit symbols
        t = re.sub(r"[\$]", " dollar ", t)
        t = re.sub(r"[€]", " euro ", t)
        t = re.sub(r"[£]", " pound ", t)
        t = re.sub(r"[%]", " percent ", t)
        # Dotted single-letter acronyms (u.s. -> us, u.k. -> uk, u.s.a. -> usa)
        t = re.sub(r"\b[a-z](?:\.[a-z])+\.?", lambda m: m.group(0).replace(".", ""), t)
        return t

    def _extract_unmatched_entities(self, claim: str, source: str) -> List[str]:
        """
        Extracts named entities from claim that have no grounding in the source context.
        Defends against NLI subword/semantic overlap illusions (e.g. 'Anne Frank' vs 'Annie Frankson',
        'Jeremy Mathew' vs 'Jeremy Mathanga', or altered dates/numbers).
        """
        nlp = getattr(self.decomposer, "nlp", None)
        if nlp is None or not claim or not source:
            return []

        doc = nlp(claim)
        source_norm = self._canonicalize_text(source)
        unmatched: List[str] = []

        # Full OntoNotes 5 NER label coverage:
        proper_labels = {
            "PERSON", "ORG", "GPE", "LOC", "FAC", "EVENT",
            "NORP", "PRODUCT", "WORK_OF_ART", "LAW", "LANGUAGE"
        }
        quant_labels = {
            "DATE", "TIME", "PERCENT", "MONEY", "QUANTITY", "ORDINAL", "CARDINAL"
        }

        for ent in doc.ents:
            ent_text = ent.text.strip()
            ent_lower = ent_text.lower()
            ent_canon = self._canonicalize_text(ent_lower)

            if ent.label_ in proper_labels:
                # If exact entity exists as whole phrase in source, it is grounded
                if re.search(rf"\b{re.escape(ent_canon)}\b", source_norm) or re.search(rf"\b{re.escape(ent_lower)}\b", source_norm):
                    continue

                # Check substantive tokens (>1 char, non-stopword, dot-stripped)
                sub_words = [
                    w.text.lower().replace(".", "")
                    for w in ent
                    if len(w.text.replace(".", "")) > 1 and not w.is_stop and not w.is_punct
                ]
                # Every substantive token in a proper entity must exist as a discrete word in source
                if any(not re.search(rf"\b{re.escape(w)}\b", source_norm) for w in sub_words):
                    unmatched.append(ent_text)

            elif ent.label_ in quant_labels:
                norm_ent = self._canonicalize_text(ent_lower)

                # 1. Whole-word boundary check for digits (prevents "100" matching inside "1000")
                digits = re.findall(r"\b\d+(?:\.\d+)?\b", norm_ent)
                digit_miss = any(not re.search(rf"\b{re.escape(d)}\b", source_norm) for d in digits)

                # 2. Check substantive words (accounting for plural s in units/currencies, e.g. dollars vs dollar)
                raw_words = [w for w in re.findall(r"\b[a-z]{3,}\b", norm_ent) if not nlp.vocab[w].is_stop]
                word_miss = False
                for w in raw_words:
                    base_w = w.rstrip("s") if len(w) > 4 and w.endswith("s") else w
                    if not (re.search(rf"\b{re.escape(w)}\b", source_norm) or re.search(rf"\b{re.escape(base_w)}\b", source_norm)):
                        word_miss = True
                        break

                if digit_miss or word_miss:
                    unmatched.append(ent_text)

        return list(dict.fromkeys(unmatched))

    def verify(
        self,
        response_text: str,
        source_info: str,
        top_k_evidence: int = 1,
        threshold: Optional[float] = None,
        source_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Executes the full end-to-end groundedness verification pipeline.

        Args:
            response_text: Unstructured prose generated by an LLM.
            source_info: Raw retrieved context documents or reference chunks.
            top_k_evidence: Maximum number of evidence candidate spans per claim (default: 1).
            threshold: Confidence threshold for entailment (defaults to self.confidence_threshold).
            source_id: Optional source document/chunk identifier.

        Returns:
            Dictionary conforming to hearsay.proxy.protocol.VerificationResult.
        """
        start_time = time.perf_counter()
        active_threshold = threshold if threshold is not None else self.confidence_threshold
        request_id = f"req-{uuid.uuid4().hex[:10]}"

        clean_response = response_text.strip() if response_text else ""
        clean_source = source_info.strip() if source_info else ""

        # Guard: empty response text
        if not clean_response:
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return {
                "request_id": request_id,
                "overall_status": "Verified",
                "groundedness_score": 100.0,
                "total_claims": 0,
                "supported_claims": 0,
                "contradicted_claims": 0,
                "ungrounded_claims": 0,
                "claims": [],
                "latency_ms": elapsed_ms,
            }

        # 1. Claim Decomposition
        claims = self.decomposer.decompose(clean_response)

        # Guard: no source info provided -> all claims ungrounded
        if not clean_source:
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
            verdicts = [
                {
                    "claim_id": idx,
                    "claim_text": claim,
                    "status": "Unsupported (Ungrounded)",
                    "confidence": 0.0,
                    "evidence_span": None,
                    "source_chunk_id": source_id,
                    "nli_logits": {"entailment": 0.0, "neutral": 1.0, "contradiction": 0.0},
                    "unmatched_entities": [],
                }
                for idx, claim in enumerate(claims)
            ]
            return {
                "request_id": request_id,
                "overall_status": "Hallucination Detected" if claims else "Verified",
                "groundedness_score": 0.0,
                "total_claims": len(claims),
                "supported_claims": 0,
                "contradicted_claims": 0,
                "ungrounded_claims": len(claims),
                "claims": verdicts,
                "latency_ms": elapsed_ms,
            }

        # 2. Evidence Retrieval & 3. NLI Classification per Claim
        verdicts: List[Dict[str, Any]] = []
        supported_count = 0
        contradicted_count = 0
        ungrounded_count = 0

        for idx, claim in enumerate(claims):
            candidates = self.retriever.get_candidate_spans(
                clean_source, claim, top_k=top_k_evidence
            )
            best_evidence = candidates[0]["chunk"] if candidates else clean_source[:2000]

            # Standard RAG passages (<= 2000 chars) are passed in full to NLI to resolve cross-sentence pronouns/antecedents
            premise_text = clean_source if len(clean_source) <= 2000 else best_evidence

            nli_result = self.verifier.predict(
                premise=premise_text,
                hypothesis=claim,
                threshold=active_threshold,
            )
            status = nli_result["status"]
            confidence = nli_result["confidence"]

            # Entity-Consistency Guardrail: Intercept semantic illusion on ungrounded entities
            unmatched_entities = self._extract_unmatched_entities(claim, clean_source)
            if unmatched_entities and status == "Supported":
                status = "Unsupported (Ungrounded Entity)"
                confidence = 0.90

            if status == "Supported":
                supported_count += 1
            elif "Contradiction" in status:
                contradicted_count += 1
            else:
                ungrounded_count += 1

            verdicts.append({
                "claim_id": idx,
                "claim_text": claim,
                "status": status,
                "confidence": confidence,
                "evidence_span": best_evidence,
                "source_chunk_id": source_id if source_id else f"chunk-{idx}",
                "nli_logits": nli_result["logits"],
                "unmatched_entities": unmatched_entities,
            })

        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
        total_claims = len(claims)
        groundedness_score = round(
            (supported_count / total_claims * 100.0) if total_claims > 0 else 100.0, 2
        )

        overall_status = (
            "Verified"
            if (ungrounded_count == 0 and contradicted_count == 0)
            else "Hallucination Detected"
        )

        return {
            "request_id": request_id,
            "overall_status": overall_status,
            "groundedness_score": groundedness_score,
            "total_claims": total_claims,
            "supported_claims": supported_count,
            "contradicted_claims": contradicted_count,
            "ungrounded_claims": ungrounded_count,
            "claims": verdicts,
            "latency_ms": elapsed_ms,
        }
