import json
from pathlib import Path
from typing import List, Dict, Any, Union
import pandas as pd


class RAGTruthLoader:
    """Loader and preprocessor for the RAGTruth benchmark dataset.

    Loads and joins source documents (`source_info.jsonl`) with model responses
    and human hallucination annotations (`response.jsonl`) on `source_id`.
    """

    def __init__(self, data_dir: Union[str, Path] = "data"):
        self.data_dir = Path(data_dir)

    def load_sources(self) -> List[Dict[str, Any]]:
        """Reads and parses source_info.jsonl."""
        source_file = self.data_dir / "source_info.jsonl"
        sources = []
        with open(source_file, "r", encoding="utf-8") as file:
            for line in file:
                if line.strip():
                    sources.append(json.loads(line))
        return sources

    def load_responses(self) -> List[Dict[str, Any]]:
        """Reads and parses response.jsonl."""
        response_file = self.data_dir / "response.jsonl"
        responses = []
        with open(response_file, "r", encoding="utf-8") as file:
            for line in file:
                if line.strip():
                    responses.append(json.loads(line))
        return responses

    def load(self) -> List[Dict[str, Any]]:
        """Loads and joins sources and responses into a list of record dicts."""
        sources = self.load_sources()
        responses = self.load_responses()

        source_map = {source["source_id"]: source for source in sources}
        dataset = []

        for response in responses:
            source = source_map.get(response["source_id"])
            if source is not None:
                dataset.append({
                    "id": response["id"],
                    "source_id": response["source_id"],
                    "model": response["model"],
                    "temperature": response["temperature"],
                    "split": response["split"],
                    "quality": response["quality"],
                    "task_type": source.get("task_type", "Unknown"),
                    "source": source["source"],
                    "source_info": source["source_info"],
                    "prompt": source["prompt"],
                    "response": response["response"],
                    "labels": response["labels"],
                })

        return dataset

    def load_joined_dataset(self) -> pd.DataFrame:
        """Loads and joins sources and responses into a pandas DataFrame.

        Fulfills the Agile Specification contract for evaluation pipelines.
        """
        return pd.DataFrame(self.load())

    def load_as_dataframe(self) -> pd.DataFrame:
        """Convenience alias for load_joined_dataset()."""
        return self.load_joined_dataset()
