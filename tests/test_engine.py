"""
Unit and integration tests for HearsayEngine verification pipeline (Days 5, 6 & 7).
"""

from unittest.mock import MagicMock
import pytest
import spacy
from hearsay.engine import HearsayEngine, ClaimDecomposer, BiEncoderRetriever, NLIClassifier
from hearsay.engine.pipeline import HearsayEngine as DirectHearsayEngine
from hearsay.proxy.protocol import VerificationResult


class MockNLIClassifier:
    """Mock verifier providing deterministic NLI responses for pipeline testing."""

    def __init__(self, mode="supported"):
        self.mode = mode

    def predict(self, premise: str, hypothesis: str, threshold: float = 0.60):
        if not premise or not hypothesis:
            return {
                "status": "Unsupported (Ungrounded)",
                "confidence": 0.0,
                "logits": {"entailment": 0.0, "neutral": 1.0, "contradiction": 0.0},
            }
        
        if self.mode == "supported":
            return {
                "status": "Supported",
                "confidence": 0.95,
                "logits": {"entailment": 0.95, "neutral": 0.03, "contradiction": 0.02},
            }
        elif self.mode == "contradicted":
            return {
                "status": "Unsupported (Contradiction)",
                "confidence": 0.88,
                "logits": {"entailment": 0.05, "neutral": 0.07, "contradiction": 0.88},
            }
        elif self.mode == "ungrounded":
            return {
                "status": "Unsupported (Ungrounded)",
                "confidence": 0.80,
                "logits": {"entailment": 0.10, "neutral": 0.80, "contradiction": 0.10},
            }
        elif self.mode == "mixed":
            # If 'not' or 'never' in hypothesis, flag as contradiction
            if any(w in hypothesis.lower() for w in ["not", "never", "fake"]):
                return {
                    "status": "Unsupported (Contradiction)",
                    "confidence": 0.85,
                    "logits": {"entailment": 0.05, "neutral": 0.10, "contradiction": 0.85},
                }
            return {
                "status": "Supported",
                "confidence": 0.92,
                "logits": {"entailment": 0.92, "neutral": 0.05, "contradiction": 0.03},
            }
        return {
            "status": "Unsupported (Ungrounded)",
            "confidence": 0.50,
            "logits": {"entailment": 0.20, "neutral": 0.50, "contradiction": 0.30},
        }


@pytest.fixture(scope="module")
def shared_nlp():
    return spacy.load("en_core_web_sm")


@pytest.fixture
def mock_retriever():
    retriever = MagicMock()
    retriever.get_candidate_spans.return_value = [
        {"chunk": "Paris is the capital of France with a large population.", "score": 0.89}
    ]
    return retriever


def test_package_export():
    """Verify HearsayEngine is properly exported from hearsay.engine."""
    assert HearsayEngine is DirectHearsayEngine


def test_empty_response_text(shared_nlp, mock_retriever):
    """Verify empty response text produces 0 claims and Verified status."""
    engine = HearsayEngine(
        decomposer=ClaimDecomposer(nlp=shared_nlp),
        retriever=mock_retriever,
        verifier=MockNLIClassifier(mode="supported"),
    )
    result = engine.verify(response_text="", source_info="Some context.")
    assert result["overall_status"] == "Verified"
    assert result["groundedness_score"] == 100.0
    assert result["total_claims"] == 0
    assert len(result["claims"]) == 0
    assert result["latency_ms"] >= 0.0


def test_empty_source_info(shared_nlp, mock_retriever):
    """Verify empty source context marks all decomposed claims as Ungrounded."""
    engine = HearsayEngine(
        decomposer=ClaimDecomposer(nlp=shared_nlp),
        retriever=mock_retriever,
        verifier=MockNLIClassifier(mode="supported"),
    )
    result = engine.verify(
        response_text="The James Webb Telescope detected water vapor.",
        source_info="",
    )
    assert result["overall_status"] == "Hallucination Detected"
    assert result["groundedness_score"] == 0.0
    assert result["total_claims"] >= 1
    assert result["ungrounded_claims"] == result["total_claims"]
    assert all(c["status"] == "Unsupported (Ungrounded)" for c in result["claims"])


def test_fully_supported_response(shared_nlp, mock_retriever):
    """Verify response with all supported claims returns Verified and 100% groundedness."""
    engine = HearsayEngine(
        decomposer=ClaimDecomposer(nlp=shared_nlp),
        retriever=mock_retriever,
        verifier=MockNLIClassifier(mode="supported"),
    )
    response = "Paris is the capital of France. It has an official population of over two million."
    source = "Paris is the capital of France with an official population exceeding two million people."
    
    result = engine.verify(response, source)
    assert result["overall_status"] == "Verified"
    assert result["groundedness_score"] == 100.0
    assert result["total_claims"] >= 1
    assert result["supported_claims"] == result["total_claims"]
    assert result["contradicted_claims"] == 0
    assert result["ungrounded_claims"] == 0


def test_contradicted_hallucination_response(shared_nlp, mock_retriever):
    """Verify contradicted claim marks overall status as Hallucination Detected."""
    engine = HearsayEngine(
        decomposer=ClaimDecomposer(nlp=shared_nlp),
        retriever=mock_retriever,
        verifier=MockNLIClassifier(mode="contradicted"),
    )
    response = "The Sun revolves around the Earth once every 24 hours."
    source = "The Earth revolves around the Sun over the course of 365 days."
    
    result = engine.verify(response, source)
    assert result["overall_status"] == "Hallucination Detected"
    assert result["groundedness_score"] == 0.0
    assert result["contradicted_claims"] >= 1
    assert result["supported_claims"] == 0


def test_mixed_claims_pipeline(shared_nlp, mock_retriever):
    """Verify pipeline properly tallies mixed supported and hallucinated claims."""
    engine = HearsayEngine(
        decomposer=ClaimDecomposer(nlp=shared_nlp),
        retriever=mock_retriever,
        verifier=MockNLIClassifier(mode="mixed"),
    )
    response = (
        "Paris is the capital of France, but it was never inhabited by Romans. "
        "The city contains famous landmarks."
    )
    source = "Paris was historically occupied by the Romans and is the capital of France."
    
    result = engine.verify(response, source)
    assert result["overall_status"] == "Hallucination Detected"
    assert 0.0 < result["groundedness_score"] < 100.0
    assert result["supported_claims"] >= 1
    assert result["contradicted_claims"] >= 1


def test_pydantic_protocol_validation(shared_nlp, mock_retriever):
    """Verify that HearsayEngine.verify output validates against VerificationResult."""
    engine = HearsayEngine(
        decomposer=ClaimDecomposer(nlp=shared_nlp),
        retriever=mock_retriever,
        verifier=MockNLIClassifier(mode="supported"),
    )
    raw_result = engine.verify("Simple claim text.", "Simple source context.")
    
    # Must validate cleanly into Pydantic v2 VerificationResult
    pydantic_obj = VerificationResult.model_validate(raw_result)
    assert pydantic_obj.request_id == raw_result["request_id"]
    assert pydantic_obj.overall_status == raw_result["overall_status"]
    assert pydantic_obj.groundedness_score == raw_result["groundedness_score"]
    assert len(pydantic_obj.claims) == len(raw_result["claims"])
