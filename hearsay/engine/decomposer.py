"""
Claim Decomposer Module for Hearsay Core ML Engine.

Decomposes unstructured LLM response prose into discrete, atomic claims
using spaCy sentence segmentation and conjunction-based clause splitting.
"""

from typing import List, Optional
import re
import spacy


def _preprocess_markdown(text: str) -> str:
    """Cleans Markdown formatting, disclaimers, and merges hanging headers."""
    # 1. Remove disclaimer parentheticals and markdown blocks like *(Note: ...)* or *Note: ...*
    text = re.sub(r"\*?\s*\((?:Note|Notice|Disclaimer):.*?\)\s*\*?", "", text, flags=re.I | re.DOTALL)
    text = re.sub(r"\*(?:Note|Notice|Disclaimer):[^\n*]*\*", "", text, flags=re.I)
    text = re.sub(r"(?:Note|Notice|Disclaimer):\s*[^\n]+", "", text, flags=re.I)
    # Remove phrases about synthetic training artefact/inaccuracies
    text = re.sub(r"[^\n.]*synthetic training artefact[^\n.]*\.?", "", text, flags=re.I)
    text = re.sub(r"[^\n.]*deliberate factual inaccuracies[^\n.]*\.?", "", text, flags=re.I)
    
    lines = text.splitlines()
    cleaned_lines = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
            
        # Check if line is an isolated bullet header like `* **Alternative Therapy:**`
        if re.match(r"^[-*•]?\s*\*\*[^*]+:\*\*\s*$", line):
            if i + 1 < len(lines) and lines[i + 1].strip():
                # Merge with following line without the colon label
                next_line = lines[i + 1].strip()
                next_line = re.sub(r"^[-*•]\s*", "", next_line)
                cleaned_lines.append(next_line)
                i += 2
                continue
            else:
                i += 1
                continue

        # Strip inline bullet headers like `* **Contraindication:** text` -> `text`
        line = re.sub(r"^[-*•]?\s*\*\*[^*]+:\*\*\s*", "", line)
        # Strip generic markdown bullets and headers
        line = re.sub(r"^[-*•]\s+", "", line)
        line = re.sub(r"^#{1,6}\s+", "", line)
        # Strip bold/italic markdown symbols
        line = re.sub(r"\*\*([^*]+)\*\*", r"\1", line)
        line = re.sub(r"\*([^*]+)\*", r"\1", line)
        
        if line.strip():
            cleaned_lines.append(line.strip())
        i += 1
        
    return " ".join(cleaned_lines)


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

        cleaned_text = _preprocess_markdown(text)
        if not cleaned_text.strip():
            return []

        doc = self.nlp(cleaned_text)

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
                    # Filter out fragments without verbs or with fewer than 3 words
                    if len(cleaned.split()) >= 3 and any(t.pos_ in {"VERB", "AUX"} for t in chunk_doc):
                        claims.append(cleaned)
                else:
                    last_idx = 0
                    for pt in split_points:
                        sub = chunk[last_idx:pt].strip().strip(",;:").strip()
                        sub_doc = self.nlp(sub)
                        if len(sub.split()) >= 3 and any(t.pos_ in {"VERB", "AUX"} for t in sub_doc):
                            claims.append(sub)
                        last_idx = pt
                    sub = chunk[last_idx:].strip()
                    sub = re.sub(r"^(?:and|but|whereas)\s+", "", sub, flags=re.I).strip().strip(",;:").strip()
                    sub_doc = self.nlp(sub)
                    if len(sub.split()) >= 3 and any(t.pos_ in {"VERB", "AUX"} for t in sub_doc):
                        claims.append(sub)

        # 3. Fallback: if splitting filtered out everything, return the cleaned raw text
        return claims if claims else [cleaned_text.strip()]