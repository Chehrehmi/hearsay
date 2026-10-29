"""
ALCE (Automatic LLMs' Citation Evaluation) Dataset Loader.
Loads ASQA, QAMPARI, and ELI5 benchmarks from Princeton NLP (EMNLP 2023, Gao et al.).
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional


class ALCELoader:
    """
    Loader for the official ALCE benchmark dataset.
    """

    def __init__(self, data_dir: Optional[Path] = None):
        if data_dir is None:
            self.data_dir = Path(__file__).resolve().parent.parent.parent / "data" / "ALCE-data"
        else:
            self.data_dir = Path(data_dir)

    def load_asqa_samples(self, n_samples: int = 30) -> List[Dict[str, Any]]:
        """
        Loads top-n samples from asqa_eval_gtr_top100_reranked_oracle.json.
        """
        file_path = self.data_dir / "asqa_eval_gtr_top100_reranked_oracle.json"
        if not file_path.exists():
            # Fallback to standard GTR top100
            file_path = self.data_dir / "asqa_eval_gtr_top100.json"

        if not file_path.exists():
            raise FileNotFoundError(f"ALCE ASQA dataset not found in {self.data_dir}")

        with open(file_path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)

        samples = []
        for item in raw_data[:n_samples]:
            docs_map = {}
            docs_text_combined = []
            for i, doc in enumerate(item.get("docs", [])[:5]):
                doc_id = str(i + 1)
                text = doc.get("text", "").strip()
                title = doc.get("title", "")
                docs_map[doc_id] = text
                docs_text_combined.append(f"[Doc {doc_id}] ({title}): {text}")

            gold_answer = ""
            if item.get("annotations") and isinstance(item["annotations"], list):
                gold_answer = item["annotations"][0].get("long_answer", "")

            samples.append({
                "sample_id": item.get("sample_id", len(samples)),
                "question": item.get("question", ""),
                "gold_answer": gold_answer,
                "docs_map": docs_map,
                "combined_context": "\n\n".join(docs_text_combined),
            })

        return samples
