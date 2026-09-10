from hearsay.proxy.protocol import (
    ClaimVerdict,
    ContextPayload,
    VerificationRequest,
    VerificationResult,
)
import pytest
from pydantic import ValidationError


# -------------------------
# ContextPayload
# -------------------------

def test_valid_context_payload():
    payload = ContextPayload(
        source_id="doc_1",
        source_info="Paris is in France"
    )

    assert payload.source_id == "doc_1"
    assert payload.source_info == "Paris is in France"


def test_context_payload_missing_source_id():
    with pytest.raises(ValidationError):
        ContextPayload(
            source_id=None,
            source_info="Paris is in France"
        )


def test_context_payload_missing_source_info():
    with pytest.raises(ValidationError):
        ContextPayload(
            source_id="doc_1",
            source_info=None
        )


# -------------------------
# VerificationRequest
# -------------------------

def test_verification_request_defaults():
    request = VerificationRequest()

    assert request.model == "gpt-3.5-turbo"
    assert request.messages == []
    assert request.response_text is None
    assert request.verirag_context is None


def test_verification_request_with_data():
    context = ContextPayload(
        source_id="doc_1",
        source_info="Paris is in France"
    )

    request = VerificationRequest(
        model="gpt-4",
        messages=[
            {"role": "user", "content": "Where is Paris?"}
        ],
        response_text="Paris is in France.",
        verirag_context=context
    )

    assert request.model == "gpt-4"
    assert len(request.messages) == 1
    assert request.response_text == "Paris is in France."
    assert request.verirag_context.source_id == "doc_1"


def test_verification_request_invalid_context():
    with pytest.raises(ValidationError):
        VerificationRequest(
            model="gpt-4",
            verirag_context={
                "source_id": None,
                "source_info": "Paris is in France"
            }
        )


# -------------------------
# ClaimVerdict
# -------------------------

def test_claim_verdict_valid():
    claim_verdict = ClaimVerdict(
        claim_id=1,
        claim_text="Paris is in France.",
        status="Supported",
        confidence=0.9
    )

    assert claim_verdict.claim_id == 1
    assert claim_verdict.claim_text == "Paris is in France."
    assert claim_verdict.status == "Supported"
    assert claim_verdict.confidence == 0.9


def test_claim_verdict_confidence_zero():
    claim_verdict = ClaimVerdict(
        claim_id=1,
        claim_text="Test claim",
        status="Supported",
        confidence=0.0
    )

    assert claim_verdict.confidence == 0.0


def test_claim_verdict_confidence_one():
    claim_verdict = ClaimVerdict(
        claim_id=1,
        claim_text="Test claim",
        status="Supported",
        confidence=1.0
    )

    assert claim_verdict.confidence == 1.0


def test_claim_verdict_invalid_confidence_above_one():
    with pytest.raises(ValidationError):
        ClaimVerdict(
            claim_id=1,
            claim_text="Tom hit Jerry",
            status="Unsupported (Contradiction)",
            confidence=1.1
        )


def test_claim_verdict_invalid_confidence_below_zero():
    with pytest.raises(ValidationError):
        ClaimVerdict(
            claim_id=1,
            claim_text="Tom hit Jerry",
            status="Unsupported (Contradiction)",
            confidence=-0.1
        )


def test_claim_verdict_optional_fields():
    claim_verdict = ClaimVerdict(
        claim_id=1,
        claim_text="Paris is in France.",
        status="Supported",
        confidence=0.95,
        evidence_span="Paris is the capital of France.",
        source_chunk_id="chunk_1",
        nli_logits={
            "entailment": 0.95,
            "contradiction": 0.03,
            "neutral": 0.02
        }
    )

    assert claim_verdict.evidence_span == "Paris is the capital of France."
    assert claim_verdict.source_chunk_id == "chunk_1"
    assert claim_verdict.nli_logits["entailment"] == 0.95


def test_claim_verdict_optional_fields_default():
    claim_verdict = ClaimVerdict(
        claim_id=1,
        claim_text="Test claim",
        status="Supported",
        confidence=0.9
    )

    assert claim_verdict.evidence_span is None
    assert claim_verdict.source_chunk_id is None
    assert claim_verdict.nli_logits == {}


# -------------------------
# VerificationResult
# -------------------------

def test_verification_result_valid():
    result = VerificationResult(
        request_id="123",
        overall_status="Verified",
        groundedness_score=90.07,
        total_claims=5,
        supported_claims=3,
        contradicted_claims=1,
        ungrounded_claims=1,
        claims=[],
        latency_ms=454.78
    )

    assert result.request_id == "123"
    assert result.overall_status == "Verified"
    assert result.groundedness_score == 90.07
    assert result.total_claims == 5
    assert result.supported_claims == 3
    assert result.contradicted_claims == 1
    assert result.ungrounded_claims == 1
    assert result.latency_ms == 454.78


def test_verification_result_negative_counts():
    with pytest.raises(ValidationError):
        VerificationResult(
            request_id="123",
            overall_status="Verified",
            groundedness_score=90.07,
            total_claims=-1,
            supported_claims=3,
            contradicted_claims=1,
            ungrounded_claims=1,
            claims=[],
            latency_ms=454.78
        )


def test_verification_result_nested_claims():
    claim = ClaimVerdict(
        claim_id=1,
        claim_text="Paris is in France.",
        status="Supported",
        confidence=0.95
    )

    result = VerificationResult(
        request_id="123",
        overall_status="Verified",
        groundedness_score=100.0,
        total_claims=1,
        supported_claims=1,
        contradicted_claims=0,
        ungrounded_claims=0,
        claims=[claim],
        latency_ms=100.0
    )

    assert len(result.claims) == 1
    assert result.claims[0].claim_id == 1
    assert result.claims[0].status == "Supported"


def test_verification_result_serialization():
    result = VerificationResult(
        request_id="123",
        overall_status="Verified",
        groundedness_score=90.07,
        total_claims=5,
        supported_claims=3,
        contradicted_claims=1,
        ungrounded_claims=1,
        claims=[],
        latency_ms=454.78
    )

    assert isinstance(result.model_dump(), dict)


def test_verification_result_json():
    result = VerificationResult(
        request_id="123",
        overall_status="Verified",
        groundedness_score=90.07,
        total_claims=5,
        supported_claims=3,
        contradicted_claims=1,
        ungrounded_claims=1,
        claims=[],
        latency_ms=454.78
    )

    assert isinstance(result.model_dump_json(), str)


def test_verification_result_invalid_groundedness_score_above_100():
    with pytest.raises(ValidationError):
        VerificationResult(
            request_id="123",
            overall_status="Verified",
            groundedness_score=105.0,  # Invalid! > 100.0
            total_claims=1,
            supported_claims=1,
            contradicted_claims=0,
            ungrounded_claims=0,
            latency_ms=10.0
        )


def test_verification_result_roundtrip_json():
    original = VerificationResult(
        request_id="123",
        overall_status="Verified",
        groundedness_score=100.0,
        total_claims=1,
        supported_claims=1,
        contradicted_claims=0,
        ungrounded_claims=0,
        claims=[
            ClaimVerdict(
                claim_id=0,
                claim_text="Paris is in France.",
                status="Supported",
                confidence=0.99
            )
        ],
        latency_ms=12.5
    )
    
    json_str = original.model_dump_json()
    # Parse it back from JSON!
    reconstructed = VerificationResult.model_validate_json(json_str)
    
    assert reconstructed.request_id == original.request_id
    assert len(reconstructed.claims) == 1
    assert reconstructed.claims[0].claim_text == "Paris is in France."


def test_claim_verdict_type_coercion():
    verdict = ClaimVerdict(
        claim_id="0",        # String should be coerced to int 0
        claim_text="Test",
        status="Supported",
        confidence="0.85"    # String should be coerced to float 0.85
    )
    assert isinstance(verdict.claim_id, int)
    assert verdict.claim_id == 0
    assert isinstance(verdict.confidence, float)
    assert verdict.confidence == 0.85
