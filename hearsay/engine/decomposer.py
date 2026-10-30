"""
Claim Decomposer Module for Hearsay Core ML Engine.

Decomposes unstructured LLM response prose into discrete, atomic claims
using spaCy sentence segmentation and conjunction-based clause splitting.
"""

from typing import List, Optional
import re
import spacy


class ClaimDecomposer:
    """
    Decomposes unstructured LLM response text into discrete, atomic claims.
    """

    _shared_nlp: Optional[spacy.language.Language] = None

    def __init__(
        self,
        model_name: str = "en_core_web_sm",
        nlp: Optional[spacy.language.Language] = None,
    ):
        """
        Initialize the ClaimDecomposer.

        Args:
            model_name: Name of the spaCy model to load (default: 'en_core_web_sm').
            nlp: Optional pre-loaded spaCy Language model instance (useful for testing).
        """
        if nlp is not None:
            self.nlp = nlp
        else:
            if ClaimDecomposer._shared_nlp is None:
                ClaimDecomposer._shared_nlp = spacy.load(model_name)
            self.nlp = ClaimDecomposer._shared_nlp

    def decompose(self, text: str) -> List[str]:
        """
        Decomposes response prose into a list of discrete atomic sentence/clause claims.

        Args:
            text: Unstructured LLM generated response string.

        Returns:
            List of atomic claim strings. Returns an empty list if input is empty or whitespace.
        """
        if not text or not text.strip():
            return []

        doc = self.nlp(text)

        # 1. Extract non-empty sentences longer than 5 characters
        sentences = [
            sent.text.strip() for sent in doc.sents if len(sent.text.strip()) > 5
        ]

        claims: List[str] = []
        for sent in sentences:
            # 2. Sub-split compound sentences on semicolons
            chunks = [c.strip() for c in sent.split(";") if c.strip()]
            for chunk in chunks:
                chunk_doc = self.nlp(chunk)
                split_points = []
                for token in chunk_doc:
                    # Conjunctions (and, but, whereas) only split if following clause has subject + verb
                    if (token.dep_ in {"cc", "mark"} or token.pos_ in {"CCONJ", "SCONJ"}) and token.text.lower() in {"and", "but", "whereas"}:
                        has_subj_after = any(t.dep_ in {"nsubj", "nsubjpass"} for t in chunk_doc[token.i+1:])
                        has_verb_after = any(t.pos_ in {"VERB", "AUX"} for t in chunk_doc[token.i+1:])
                        if has_subj_after and has_verb_after:
                            split_points.append(token.idx)

                if not split_points:
                    cleaned = chunk.strip().strip(",;:").strip()
                    if len(cleaned.split()) >= 3:
                        claims.append(cleaned)
                else:
                    last_idx = 0
                    for pt in split_points:
                        sub = chunk[last_idx:pt].strip().strip(",;:").strip()
                        if len(sub.split()) >= 3:
                            claims.append(sub)
                        last_idx = pt
                    sub = chunk[last_idx:].strip()
                    sub = re.sub(r"^(?:and|but|whereas)\s+", "", sub, flags=re.I).strip().strip(",;:").strip()
                    if len(sub.split()) >= 3:
                        claims.append(sub)

        # 3. Fallback: if splitting filtered out everything, return the cleaned raw text
        return claims if claims else [text.strip()]