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


def test_entity_mismatch_interception(shared_nlp, mock_retriever):
    """Verify that ungrounded named entities override naive NLI entailment into Ungrounded Entity."""
    engine = HearsayEngine(
        decomposer=ClaimDecomposer(nlp=shared_nlp),
        retriever=mock_retriever,
        verifier=MockNLIClassifier(mode="supported"), # Naive NLI says Supported
    )
    # Claim contains ungrounded entity 'Annie Frankson'
    result = engine.verify(
        response_text="Annie Frankson was an author.",
        source_info="Anne Frank died in 1945.",
    )
    assert result["overall_status"] == "Hallucination Detected"
    assert result["groundedness_score"] == 0.0
    assert result["claims"][0]["status"] == "Unsupported (Ungrounded Entity)"
    assert "Annie Frankson" in result["claims"][0]["unmatched_entities"]


def test_extended_entity_types_interception(shared_nlp, mock_retriever):
    """Verify that ungrounded NORP, PERCENT, QUANTITY, and ORDINAL entities are intercepted."""
    engine = HearsayEngine(
        decomposer=ClaimDecomposer(nlp=shared_nlp),
        retriever=mock_retriever,
        verifier=MockNLIClassifier(mode="supported"),
    )
    # 1. NORP (nationality) mismatch
    r1 = engine.verify("Kant was a French philosopher.", "Kant was a German philosopher.")
    assert "French" in r1["claims"][0]["unmatched_entities"]
    assert r1["claims"][0]["status"] == "Unsupported (Ungrounded Entity)"

    # 2. PERCENT mismatch
    r2 = engine.verify("Revenue grew by 50 percent in 2023.", "Revenue grew by 5 percent in 2023.")
    assert any("50" in ent for ent in r2["claims"][0]["unmatched_entities"])
    assert r2["claims"][0]["status"] == "Unsupported (Ungrounded Entity)"

    # 3. QUANTITY mismatch
    r3 = engine.verify("Aircraft reached 900 mph.", "Aircraft reached 500 mph.")
    assert any("900" in ent for ent in r3["claims"][0]["unmatched_entities"])
    assert r3["claims"][0]["status"] == "Unsupported (Ungrounded Entity)"


def test_ordinal_date_grounding(shared_nlp, mock_retriever):
    """Verify natural ordinal date verbalization ('15th of August') matches numeric date ('August 15')."""
    engine = HearsayEngine(
        decomposer=ClaimDecomposer(nlp=shared_nlp),
        retriever=mock_retriever,
        verifier=MockNLIClassifier(mode="supported"),
    )
    source = "India achieved independence from British rule on August 15, 1947, following the passage of the Indian Independence Act."

    # 1. Grounded ordinal format
    r_valid = engine.verify("Independence was achieved by India on 15th of August 1947.", source)
    assert r_valid["claims"][0]["unmatched_entities"] == []
    assert r_valid["claims"][0]["status"] == "Supported"
    assert r_valid["overall_status"] == "Verified"

    # 2. Hallucinated ordinal day
    r_halluc = engine.verify("Independence was achieved by India on 16th of August 1947.", source)
    assert any("16" in ent for ent in r_halluc["claims"][0]["unmatched_entities"])
    assert r_halluc["claims"][0]["status"] == "Unsupported (Ungrounded Entity)"
    assert r_halluc["overall_status"] == "Hallucination Detected"


def test_cross_sentence_pronoun_grounding(shared_nlp, mock_retriever):
    """Verify that multi-sentence passage premise resolves pronoun coreference."""
    engine = HearsayEngine(
        decomposer=ClaimDecomposer(nlp=shared_nlp),
        retriever=mock_retriever,
        verifier=MockNLIClassifier(mode="supported"),
    )
    source = "Steve Jobs co-founded Apple in 1976. He served as chief executive officer until 2011."
    claim = "Steve Jobs served as chief executive officer of Apple until 2011."
    res = engine.verify(claim, source)
    assert res["claims"][0]["status"] == "Supported"
    assert res["overall_status"] == "Verified"


def test_currency_symbol_verbalization_grounding(shared_nlp, mock_retriever):
    """Verify that currency symbols ($50M) match verbalized words (50 million dollars)."""
    engine = HearsayEngine(
        decomposer=ClaimDecomposer(nlp=shared_nlp),
        retriever=mock_retriever,
        verifier=MockNLIClassifier(mode="supported"),
    )
    source = "The total acquisition cost was $50 million in 2021."
    claim = "The total acquisition cost was 50 million dollars in 2021."
    res = engine.verify(claim, source)
    assert res["claims"][0]["unmatched_entities"] == []
    assert res["claims"][0]["status"] == "Supported"
    assert res["overall_status"] == "Verified"


def test_dotted_acronym_and_decimal_grounding(shared_nlp, mock_retriever):
    """Verify that dotted acronyms (U.S. vs US) and decimals (.0) are canonicalized correctly."""
    engine = HearsayEngine(
        decomposer=ClaimDecomposer(nlp=shared_nlp),
        retriever=mock_retriever,
        verifier=MockNLIClassifier(mode="supported"),
    )
    # 1. Claim U.S. vs Source US
    source1 = "The US government approved the bill in 2024."
    claim1 = "The U.S. government approved the bill in 2024."
    r1 = engine.verify(claim1, source1)
    assert r1["claims"][0]["unmatched_entities"] == []
    assert r1["claims"][0]["status"] == "Supported"

    # 2. Claim US vs Source U.S.
    source2 = "The U.S. government approved the bill in 2024."
    claim2 = "The US government approved the bill in 2024."
    r2 = engine.verify(claim2, source2)
    assert r2["claims"][0]["unmatched_entities"] == []
    assert r2["claims"][0]["status"] == "Supported"

    # 3. Decimal trailing zero (.0)
    source3 = "The inflation rate reached 5% in 2023."
    claim3 = "The inflation rate reached 5.0% in 2023."
    r3 = engine.verify(claim3, source3)
    assert r3["claims"][0]["unmatched_entities"] == []
    assert r3["claims"][0]["status"] == "Supported"
