"""
Unit tests for Hearsay NLIClassifier module (Day 4).
"""

from unittest.mock import MagicMock
import pytest
import torch
from hearsay.engine import NLIClassifier
from hearsay.engine.verifier import NLIClassifier as DirectNLIClassifier
from hearsay.proxy.protocol import ClaimVerdict


class DummyConfig:
    def __init__(self):
        self.id2label = {0: "contradiction", 1: "entailment", 2: "neutral"}


class DummyModelOutputs:
    def __init__(self, logits):
        self.logits = logits


def create_mock_nli_classifier(entailment=0.85, contradiction=0.05, neutral=0.10):
    """
    Creates an NLIClassifier instance with a mocked model and tokenizer
    that outputs the specified probability distribution.
    """
    mock_model = MagicMock()
    mock_model.config = DummyConfig()
    
    # Calculate logit tensor corresponding to desired softmax probs
    logits = torch.log(torch.tensor([[contradiction, entailment, neutral]], dtype=torch.float32))
    mock_model.return_value = DummyModelOutputs(logits)
    
    mock_tokenizer = MagicMock()
    mock_tokenizer.return_value = {
        "input_ids": torch.tensor([[101, 102]]),
        "attention_mask": torch.tensor([[1, 1]]),
    }
    
    return NLIClassifier(
        model_name="mock-model",
        model=mock_model,
        tokenizer=mock_tokenizer,
        device="cpu",
    )


def test_package_export():
    """Verify NLIClassifier is properly exported from hearsay.engine."""
    assert NLIClassifier is DirectNLIClassifier


def test_empty_and_whitespace_inputs():
    """Verify that empty premise or hypothesis produces an ungrounded result."""
    classifier = create_mock_nli_classifier()
    
    res1 = classifier.predict(premise="", hypothesis="Valid hypothesis.")
    assert res1["status"] == "Unsupported (Ungrounded)"
    assert res1["confidence"] == 0.0
    
    res2 = classifier.predict(premise="Valid premise.", hypothesis="   ")
    assert res2["status"] == "Unsupported (Ungrounded)"
    assert res2["confidence"] == 0.0

    res3 = classifier.predict(premise="   ", hypothesis="\n\t")
    assert res3["status"] == "Unsupported (Ungrounded)"
    assert res3["confidence"] == 0.0


def test_entailment_supported():
    """Verify high entailment produces 'Supported' status with matching confidence."""
    classifier = create_mock_nli_classifier(entailment=0.92, contradiction=0.03, neutral=0.05)
    result = classifier.predict(
        premise="Paris is the capital of France.",
        hypothesis="Paris is the capital city.",
    )
    assert result["status"] == "Supported"
    assert result["confidence"] == 0.92
    assert result["logits"]["entailment"] == 0.92
    assert result["logits"]["contradiction"] == 0.03
    assert result["logits"]["neutral"] == 0.05


def test_contradiction():
    """Verify high contradiction produces 'Unsupported (Contradiction)'."""
    classifier = create_mock_nli_classifier(entailment=0.02, contradiction=0.91, neutral=0.07)
    result = classifier.predict(
        premise="The Earth revolves around the Sun.",
        hypothesis="The Sun revolves around the Earth.",
    )
    assert result["status"] == "Unsupported (Contradiction)"
    assert result["confidence"] == 0.91
    assert result["logits"]["contradiction"] == 0.91


def test_neutral_ungrounded():
    """Verify neutral/unrelated evidence produces 'Unsupported (Ungrounded)'."""
    classifier = create_mock_nli_classifier(entailment=0.15, contradiction=0.10, neutral=0.75)
    result = classifier.predict(
        premise="Water boils at 100 degrees Celsius.",
        hypothesis="Albert Einstein loved apples.",
    )
    assert result["status"] == "Unsupported (Ungrounded)"
    assert result["confidence"] == 0.85


def test_custom_threshold_calibration():
    """Verify custom threshold parameter (Day 6 calibration) adjusts classification."""
    # Entailment is 0.62, above default 0.60 but below strict calibrated 0.65
    classifier = create_mock_nli_classifier(entailment=0.62, contradiction=0.08, neutral=0.30)
    
    # Default threshold (0.60) -> Supported
    res_default = classifier.predict("premise", "hypothesis", threshold=0.60)
    assert res_default["status"] == "Supported"
    
    # Calibrated threshold (0.65) -> Ungrounded
    res_calibrated = classifier.predict("premise", "hypothesis", threshold=0.65)
    assert res_calibrated["status"] == "Unsupported (Ungrounded)"


def test_claim_verdict_pydantic_compatibility():
    """Verify prediction output fits cleanly into the Pydantic ClaimVerdict schema."""
    classifier = create_mock_nli_classifier(entailment=0.88, contradiction=0.04, neutral=0.08)
    res = classifier.predict("Sample premise", "Sample hypothesis")
    
    verdict = ClaimVerdict(
        claim_id=0,
        claim_text="Sample hypothesis",
        status=res["status"],
        confidence=res["confidence"],
        evidence_span="Sample premise",
        nli_logits=res["logits"],
    )
    assert verdict.status == "Supported"
    assert verdict.confidence == 0.88
    assert verdict.nli_logits["entailment"] == 0.88
