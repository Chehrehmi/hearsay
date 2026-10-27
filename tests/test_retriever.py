"""Unit tests for Hearsay BiEncoderRetriever module."""

import pytest
import spacy
from sentence_transformers import SentenceTransformer
from hearsay.engine import BiEncoderRetriever
from hearsay.engine.retriever import BiEncoderRetriever as DirectBiEncoderRetriever


@pytest.fixture(scope="module")
def shared_nlp():
    """Share loaded spaCy model across tests in this module."""
    return spacy.load("en_core_web_sm")


@pytest.fixture(scope="module")
def shared_encoder():
    """Share loaded SentenceTransformer model across tests in this module."""
    return SentenceTransformer("all-MiniLM-L6-v2")


@pytest.fixture
def retriever(shared_encoder, shared_nlp):
    """Fixture providing a BiEncoderRetriever instance with pre-loaded models."""
    return BiEncoderRetriever(model=shared_encoder, nlp=shared_nlp)


def test_package_export():
    """Verify BiEncoderRetriever is properly exported from hearsay.engine."""
    assert BiEncoderRetriever is DirectBiEncoderRetriever


def test_initialization():
    """Verify default initialization loads models without error."""
    instance = BiEncoderRetriever()
    assert instance.model is not None
    assert instance.nlp is not None


def test_empty_and_whitespace_inputs(retriever):
    """Verify empty or None source_info or claim returns an empty list."""
    assert retriever.get_candidate_spans("", "Some claim") == []
    assert retriever.get_candidate_spans("   ", "Some claim") == []
    assert retriever.get_candidate_spans(None, "Some claim") == []
    assert retriever.get_candidate_spans("Some source text that is long enough.", "") == []
    assert retriever.get_candidate_spans("Some source text that is long enough.", "   ") == []
    assert retriever.get_candidate_spans("Some source text that is long enough.", None) == []
    assert retriever.get_candidate_spans("Some source text that is long enough.", "Claim", top_k=0) == []
    assert retriever.get_candidate_spans("Some source text that is long enough.", "Claim", top_k=-1) == []


def test_semantic_ranking_relevance(retriever):
    """Verify retriever ranks the most semantically relevant candidate sentence highest."""
    source_info = (
        "The Apollo program was an American spaceflight effort conducted by NASA in the 1960s. "
        "Apollo 11 launched from Kennedy Space Center on July 16, 1969. "
        "Commander Neil Armstrong and lunar module pilot Buzz Aldrin formed the crew that landed on the Moon. "
        "Command module pilot Michael Collins remained in lunar orbit."
    )
    claim = "Neil Armstrong landed on the Moon with Buzz Aldrin."
    candidates = retriever.get_candidate_spans(source_info, claim, top_k=3)

    assert len(candidates) == 3
    # The top candidate must be the sentence discussing Neil Armstrong and Buzz Aldrin landing
    top_candidate = candidates[0]
    assert "Neil Armstrong" in top_candidate["chunk"]
    assert "Buzz Aldrin" in top_candidate["chunk"]
    assert top_candidate["score"] >= 0.70


def test_top_k_limits(retriever):
    """Verify top_k constraints work when top_k is smaller or larger than available sentences."""
    source_info = (
        "First sentence here with enough length. "
        "Second sentence here with enough length. "
        "Third sentence here with enough length."
    )
    claim = "First sentence query."

    # top_k = 1
    res_1 = retriever.get_candidate_spans(source_info, claim, top_k=1)
    assert len(res_1) == 1

    # top_k = 2
    res_2 = retriever.get_candidate_spans(source_info, claim, top_k=2)
    assert len(res_2) == 2

    # top_k = 10 (exceeds 3 available sentences) -> should cap at 3
    res_10 = retriever.get_candidate_spans(source_info, claim, top_k=10)
    assert len(res_10) == 3


def test_scores_are_sorted_descending(retriever):
    """Verify candidate evidence spans are returned in descending order of similarity."""
    source_info = (
        "Photosynthesis allows green plants to convert solar light into chemical energy. "
        "The process generates glucose and releases oxygen gas as a byproduct. "
        "In contrast, automotive combustion engines burn petroleum fuel."
    )
    claim = "Plants generate oxygen through photosynthesis."
    candidates = retriever.get_candidate_spans(source_info, claim, top_k=3)

    scores = [c["score"] for c in candidates]
    assert scores == sorted(scores, reverse=True)


def test_sub_threshold_source_fallback(retriever):
    """Verify source shorter than 10-char threshold falls back with score 1.0."""
    short_source = "Note."
    claim = "Any claim to test."
    candidates = retriever.get_candidate_spans(short_source, claim)

    assert len(candidates) == 1
    assert candidates[0]["chunk"] == "Note."
    assert candidates[0]["score"] == 1.0


def test_single_sentence_source(retriever):
    """Verify single sentence source above threshold produces computed similarity score."""
    single_source = "The speed of light in a vacuum is 299,792 kilometers per second."
    claim = "Light travels at nearly 300,000 km per second."
    candidates = retriever.get_candidate_spans(single_source, claim)

    assert len(candidates) == 1
    assert candidates[0]["chunk"] == single_source
    assert candidates[0]["score"] >= 0.70
