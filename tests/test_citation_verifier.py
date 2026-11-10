"""
Unit tests for Path A: CitationVerifier and ALCE metrics.
"""

from hearsay.engine.citation_verifier import CitationVerifier
from hearsay.engine.verifier import NLIClassifier


class MockNLIClassifier:
    """Deterministic mock classifier for citation testing."""

    def predict(self, premise: str, hypothesis: str, threshold: float = 0.60):
        if "1969" in premise and "1969" in hypothesis:
            return {"status": "Supported", "confidence": 0.98}
        if "Mars" in hypothesis and "Moon" in premise:
            return {"status": "Unsupported (Contradiction)", "confidence": 0.95}
        return {"status": "Unsupported (Ungrounded)", "confidence": 0.70}


def test_citation_extraction():
    verifier = CitationVerifier(classifier=MockNLIClassifier())
    text = "Apollo 11 landed on the Moon in July 1969 [1]. It was launched from Florida [Doc 2, 3]."
    claims = verifier.extract_cited_claims(text)
    assert len(claims) == 2
    assert claims[0]["cited_doc_ids"] == ["1"]
    assert claims[1]["cited_doc_ids"] == ["2", "3"]
    assert "Apollo 11 landed on the Moon in July 1969" in claims[0]["clean_claim"]


def test_citation_verification_metrics():
    verifier = CitationVerifier(classifier=MockNLIClassifier())
    text = (
        "Apollo 11 landed on the Moon in July 1969 [1]. "
        "The spacecraft touched down on Mars [2]."
    )
    docs = {
        "1": "Apollo 11 was launched in 1969 and landed on the Moon.",
        "2": "The mission landed on the Moon, not on any planet.",
    }
    result = verifier.verify_citations(text, docs)
    assert result["total_claims"] == 2
    assert result["total_citations_provided"] == 2
    assert result["supported_citations"] == 1
    assert result["citation_precision"] == 50.0  # 1 out of 2 valid
    assert result["citation_recall"] == 50.0  # 1 out of 2 claims supported
    assert result["claims"][0]["citations"][0]["valid"] is True
    assert result["claims"][1]["citations"][0]["valid"] is False
    assert result["claims"][1]["citations"][0]["status"] == "Citation Hallucination"
