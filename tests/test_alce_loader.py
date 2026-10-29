"""
Unit tests for ALCELoader.
"""

from hearsay.dataset.alce_loader import ALCELoader


def test_alce_loader_loads_samples():
    loader = ALCELoader()
    samples = loader.load_asqa_samples(n_samples=3)
    assert len(samples) == 3
    assert "question" in samples[0]
    assert "docs_map" in samples[0]
    assert len(samples[0]["docs_map"]) > 0
    assert "combined_context" in samples[0]
