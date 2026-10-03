"""Unit tests for Hearsay ClaimDecomposer module."""

import pytest
import spacy
from hearsay.engine import ClaimDecomposer
from hearsay.engine.decomposer import ClaimDecomposer as DirectClaimDecomposer


@pytest.fixture(scope="module")
def shared_nlp():
    """Share loaded spaCy model across tests in this module for speed."""
    return spacy.load("en_core_web_sm")


@pytest.fixture
def decomposer(shared_nlp):
    """Fixture providing a ClaimDecomposer instance using shared nlp."""
    return ClaimDecomposer(nlp=shared_nlp)


def test_package_export():
    """Verify ClaimDecomposer is properly exported from hearsay.engine."""
    assert ClaimDecomposer is DirectClaimDecomposer


def test_initialization():
    """Verify default initialization loads spaCy model without error."""
    decomposer_instance = ClaimDecomposer()
    assert decomposer_instance.nlp is not None


def test_empty_and_whitespace_inputs(decomposer):
    """Verify that empty, None, and whitespace strings return an empty list."""
    assert decomposer.decompose("") == []
    assert decomposer.decompose("   ") == []
    assert decomposer.decompose("\n\t  \n") == []
    assert decomposer.decompose(None) == []


def test_simple_single_sentence(decomposer):
    """Verify that a standard simple sentence produces a single claim."""
    text = "The James Webb Space Telescope detected water vapor in the atmosphere."
    claims = decomposer.decompose(text)
    assert len(claims) == 1
    assert "James Webb Space Telescope" in claims[0]


def test_compound_sentence_conjunction_and(decomposer):
    """Verify compound sentence splitting on 'and'."""
    text = "Paris is the capital of France, and it has an official population of two million."
    claims = decomposer.decompose(text)
    assert len(claims) == 2
    assert claims[0] == "Paris is the capital of France"
    assert "it has an official population" in claims[1]


def test_compound_sentence_conjunction_but(decomposer):
    """Verify compound sentence splitting on 'but'."""
    text = "The medication shows high clinical efficacy, but it causes mild headaches in patients."
    claims = decomposer.decompose(text)
    assert len(claims) == 2
    assert "The medication shows high clinical efficacy" in claims[0]
    assert "it causes mild headaches in patients" in claims[1]


def test_compound_sentence_conjunction_whereas(decomposer):
    """Verify compound sentence splitting on 'whereas'."""
    text = "Solar panels produce renewable energy, whereas fossil fuels release greenhouse gases."
    claims = decomposer.decompose(text)
    assert len(claims) == 2
    assert "Solar panels produce renewable energy" in claims[0]
    assert "fossil fuels release greenhouse gases" in claims[1]


def test_compound_sentence_semicolon(decomposer):
    """Verify compound sentence splitting on semicolons."""
    text = "The laboratory verified all sample records; the project entered its final phase."
    claims = decomposer.decompose(text)
    assert len(claims) == 2
    assert "The laboratory verified all sample records" in claims[0]
    assert "the project entered its final phase" in claims[1]


def test_multi_sentence_paragraph(decomposer):
    """Verify decomposition across a full multi-sentence paragraph."""
    text = (
        "Apollo 11 landed on the Moon in July 1969. Neil Armstrong took the first historic step, "
        "and Buzz Aldrin joined him shortly thereafter. The mission concluded safely."
    )
    claims = decomposer.decompose(text)
    assert len(claims) >= 3
    assert any("Apollo 11 landed on the Moon" in c for c in claims)
    assert any("Neil Armstrong took the first historic step" in c for c in claims)
    assert any("Buzz Aldrin joined him" in c for c in claims)


def test_punctuation_stripping(decomposer):
    """Verify leading and trailing punctuation are stripped cleanly from claims."""
    text = "First claim is here, and second claim is here; third claim is here."
    claims = decomposer.decompose(text)
    for claim in claims:
        assert not claim.startswith(",")
        assert not claim.startswith(";")
        assert not claim.endswith(",")
        assert not claim.endswith(";")


def test_short_fragment_filtering_and_fallback(decomposer):
    """Verify very short words or fragments are filtered or preserved as whole text."""
    short_text = "It works."
    claims = decomposer.decompose(short_text)
    assert len(claims) == 1
    assert claims[0] == "It works."
