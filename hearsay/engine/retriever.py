"""
Bi-Encoder Retriever Module for Hearsay Core ML Engine.

Indexes retrieved source context chunks by sentence and identifies top-k candidate
evidence spans using semantic vector similarity with all-MiniLM-L6-v2.
"""

from typing import List, Dict, Any, Optional
from sentence_transformers import SentenceTransformer, util
import spacy


class BiEncoderRetriever:
    """
    Ranks and extracts candidate evidence spans from retrieved RAG context
    using bi-encoder cosine similarity.
    """

    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        model: Optional[SentenceTransformer] = None,
        nlp: Optional[spacy.language.Language] = None,
    ):
        """
        Initialize the BiEncoderRetriever.

        Args:
            model_name: HuggingFace model identifier for SentenceTransformer (default: 'all-MiniLM-L6-v2').
            model: Optional pre-loaded SentenceTransformer instance (for testing/performance).
            nlp: Optional pre-loaded spaCy Language model instance (for testing/performance).
        """
        self.model_name = model_name
        self.model = model if model is not None else SentenceTransformer(model_name)
        self.nlp = nlp if nlp is not None else spacy.load("en_core_web_sm")

    def get_candidate_spans(
        self,
        source_info: str,
        claim: str,
        top_k: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        Chunks source_info by sentence and ranks top-k candidate evidence spans by bi-encoder similarity.

        Args:
            source_info: Raw retrieved context document or concatenated chunks.
            claim: Single atomic claim string to search evidence for.
            top_k: Maximum number of candidate evidence spans to return (default: 3).

        Returns:
            List of dicts formatted as: [{"chunk": str, "score": float}, ...]
        """
        if not source_info or not source_info.strip():
            return []
        if not claim or not claim.strip():
            return []
        if top_k <= 0:
            return []

        doc = self.nlp(source_info)
        source_sentences = [
            sent.text.strip() for sent in doc.sents if len(sent.text.strip()) > 10
        ]

        # Fallback if text is shorter than threshold or sentence splitter produced no valid chunks
        if not source_sentences:
            return [{"chunk": source_info.strip(), "score": 1.0}]

        # Encode claim and candidate sentences
        claim_embedding = self.model.encode(claim.strip(), convert_to_tensor=True)
        chunk_embeddings = self.model.encode(source_sentences, convert_to_tensor=True)

        # Compute cosine similarity
        scores = util.cos_sim(claim_embedding, chunk_embeddings)[0]
        k = min(top_k, len(source_sentences))
        top_results = scores.topk(k=k)

        candidates: List[Dict[str, Any]] = []
        for score, idx in zip(top_results.values, top_results.indices):
            candidates.append({
                "chunk": source_sentences[idx.item()],
                "score": round(float(score.item()), 4),
            })

        return candidates
