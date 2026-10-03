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
            self.nlp = spacy.load(model_name)

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
            # 2. Sub-split compound sentences on semicolons and coordinating conjunctions
            sub_clauses = re.split(r';|\b(?:and|but|whereas)\b', sent)
            for clause in sub_clauses:
                # 3. Strip trailing/leading punctuation like commas and whitespace
                cleaned = clause.strip().strip(",;:").strip()

                # 4. Retain claims that have at least 3 words to avoid trivial fragments
                if len(cleaned.split()) >= 3:
                    claims.append(cleaned)

        # 5. Fallback: if splitting filtered out everything, return the cleaned raw text
        return claims if claims else [text.strip()]