import pytest
from hearsay.eval import RAGTruthAligner


def test_aligner_package_export():
    from hearsay.eval import RAGTruthAligner as ExportedAligner
    assert ExportedAligner is RAGTruthAligner


def test_aligner_no_hallucination_labels():
    response_text = "The Earth revolves around the Sun. The Moon revolves around the Earth."
    sentences = ["The Earth revolves around the Sun.", "The Moon revolves around the Earth."]
    labels = []

    aligned = RAGTruthAligner.align_sentence_labels(response_text, labels, sentences)

    assert len(aligned) == 2
    assert aligned[0]["is_hallucination"] == 0
    assert aligned[0]["label_type"] == "Supported"
    assert aligned[1]["is_hallucination"] == 0
    assert aligned[1]["label_type"] == "Supported"


def test_aligner_exact_sentence_hallucination():
    response_text = "Apollo 11 landed on the moon in 1969. Humans first walked on Mars in 1995. NASA is planning Artemis."
    sentences = [
        "Apollo 11 landed on the moon in 1969.",
        "Humans first walked on Mars in 1995.",
        "NASA is planning Artemis."
    ]
    sent2_start = response_text.find("Humans first walked on Mars in 1995.")
    sent2_end = sent2_start + len("Humans first walked on Mars in 1995.")

    labels = [{
        "start": sent2_start,
        "end": sent2_end,
        "label_type": "Evident Conflict"
    }]

    aligned = RAGTruthAligner.align_sentence_labels(response_text, labels, sentences)

    assert len(aligned) == 3
    assert aligned[0]["is_hallucination"] == 0
    assert aligned[0]["label_type"] == "Supported"

    assert aligned[1]["is_hallucination"] == 1
    assert aligned[1]["label_type"] == "Evident Conflict"
    assert aligned[1]["start"] == sent2_start
    assert aligned[1]["end"] == sent2_end

    assert aligned[2]["is_hallucination"] == 0
    assert aligned[2]["label_type"] == "Supported"


def test_aligner_partial_span_overlap():
    response_text = "First sentence here. Second sentence here."
    sentences = ["First sentence here.", "Second sentence here."]

    labels = [{"start": 15, "end": 25, "label_type": "Subtle Baseless Info"}]

    aligned = RAGTruthAligner.align_sentence_labels(response_text, labels, sentences)

    assert len(aligned) == 2
    assert aligned[0]["is_hallucination"] == 1
    assert aligned[0]["label_type"] == "Subtle Baseless Info"
    assert aligned[1]["is_hallucination"] == 1
    assert aligned[1]["label_type"] == "Subtle Baseless Info"


def test_aligner_handles_none_or_missing_labels():
    response_text = "Single sentence response."
    sentences = ["Single sentence response."]

    aligned = RAGTruthAligner.align_sentence_labels(response_text, None, sentences)

    assert len(aligned) == 1
    assert aligned[0]["is_hallucination"] == 0
    assert aligned[0]["label_type"] == "Supported"
