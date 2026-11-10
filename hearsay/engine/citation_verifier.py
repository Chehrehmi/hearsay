"""
Path A: Explicit Citation-Binding Verifier for Hearsay Engine.

Evaluates RAG generated responses containing bracketed citations (e.g., [1], [Doc 2]).
Implements the official evaluation metrics from ALCE (Gao et al., EMNLP 2023, Princeton NLP):
- Citation Precision: Proportion of citations that actually support the cited claim.
- Citation Recall: Proportion of verifiable claims that have at least one supporting citation.
- Citation Hallucination Flagging: Pinpoints invalid citations where context does not entail statement.
"""

import re
from typing import Dict, Any, List, Optional
from hearsay.engine.verifier import NLIClassifier


class CitationVerifier:
    """
    Verifies claim-level citation binding against retrieved document passages.
    """

    def __init__(self, classifier: Optional[NLIClassifier] = None):
        if classifier is not None:
            self.classifier = classifier
        else:
            self.classifier = NLIClassifier()

    def extract_cited_claims(self, text: str) -> List[Dict[str, Any]]:
        """
        Parses sentences and extracts associated citation brackets like [1], [Doc 2], [1, 2].
        """
        # Split text into sentences
        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if s.strip()]
        extracted = []

        citation_regex = re.compile(r'\[(?:Doc\s*|Document\s*)?(\d+(?:\s*,\s*(?:Doc\s*|Document\s*)?\d+)*)\]', re.IGNORECASE)

        for sent_idx, sent in enumerate(sentences):
            # Find all citation matches in the sentence
            matches = citation_regex.findall(sent)
            cited_ids = []
            for match in matches:
                # Split comma-separated IDs like "1, 2"
                ids = [re.sub(r'[^\d]', '', x) for x in match.split(',')]
                cited_ids.extend([x for x in ids if x])

            # Clean citation brackets from sentence text for clean NLI evaluation
            clean_claim = citation_regex.sub('', sent).strip()
            # Remove lingering punctuation artifacts
            clean_claim = re.sub(r'\s+', ' ', clean_claim)

            extracted.append({
                "claim_index": sent_idx,
                "raw_sentence": sent,
                "clean_claim": clean_claim,
                "cited_doc_ids": list(dict.fromkeys(cited_ids)), # remove duplicates
                "has_citations": len(cited_ids) > 0,
            })

        return extracted

    def verify_citations(
        self,
        response_text: str,
        documents: Dict[str, str],
        threshold: float = 0.60,
    ) -> Dict[str, Any]:
        """
        Performs citation-binding verification against a dictionary of {doc_id: doc_text}.

        Returns ALCE Citation Precision, Citation Recall, and per-claim verification breakdown.
        """
        claims = self.extract_cited_claims(response_text)
        verified_claims = []

        total_citations_provided = 0
        supported_citations_count = 0
        claims_with_supported_citation = 0
        total_verifiable_claims = len(claims)

        for c in claims:
            cited_ids = c["cited_doc_ids"]
            claim_text = c["clean_claim"]
            has_citations = c["has_citations"]

            citations_status = []
            claim_is_supported_by_any_citation = False

            if has_citations:
                for doc_id in cited_ids:
                    total_citations_provided += 1
                    doc_content = documents.get(str(doc_id)) or documents.get(f"doc_{doc_id}") or ""

                    if not doc_content:
                        citations_status.append({
                            "doc_id": doc_id,
                            "status": "Missing Document",
                            "confidence": 0.0,
                            "valid": False,
                        })
                        continue

                    # Check NLI entailment between cited document chunk and claim
                    res = self.classifier.predict(premise=doc_content, hypothesis=claim_text, threshold=threshold)
                    is_valid = (res.get("status") == "Supported")

                    if is_valid:
                        supported_citations_count += 1
                        claim_is_supported_by_any_citation = True

                    citations_status.append({
                        "doc_id": doc_id,
                        "status": "Valid Citation" if is_valid else "Citation Hallucination",
                        "nli_status": res.get("status"),
                        "confidence": res.get("confidence", 0.0),
                        "evidence_snippet": doc_content[:200] + "..." if len(doc_content) > 200 else doc_content,
                        "valid": is_valid,
                    })

                if claim_is_supported_by_any_citation:
                    claims_with_supported_citation += 1

                overall_claim_status = "Supported" if claim_is_supported_by_any_citation else "Unsupported (Citation Hallucination)"
            else:
                # Claim without citation
                overall_claim_status = "Uncited Prose"

            verified_claims.append({
                "claim_index": c["claim_index"],
                "raw_sentence": c["raw_sentence"],
                "clean_claim": claim_text,
                "has_citations": has_citations,
                "overall_status": overall_claim_status,
                "citations": citations_status,
            })

        # ALCE Standard Metrics (EMNLP 2023)
        citation_precision = (
            round((supported_citations_count / total_citations_provided) * 100.0, 1)
            if total_citations_provided > 0
            else 0.0
        )
        citation_recall = (
            round((claims_with_supported_citation / total_verifiable_claims) * 100.0, 1)
            if total_verifiable_claims > 0
            else 0.0
        )

        return {
            "total_claims": total_verifiable_claims,
            "total_citations_provided": total_citations_provided,
            "supported_citations": supported_citations_count,
            "citation_precision": citation_precision,
            "citation_recall": citation_recall,
            "overall_status": "Citation Verified" if (citation_precision >= 80.0 and citation_recall >= 70.0) else "Citation Hallucinations Flagged",
            "claims": verified_claims,
        }
