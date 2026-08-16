import json
from pathlib import Path


class RAGTruthLoader:
    def __init__(self, data_dir):
        self.data_dir = Path(data_dir)

    def load_sources(self):
        source_file = self.data_dir / "source_info.jsonl"

        sources = []

        with open(source_file, "r", encoding="utf-8") as file:
            for line in file:
                sources.append(json.loads(line))

        return sources

    def load_responses(self):
        response_file = self.data_dir / "response.jsonl"

        responses = []

        with open(response_file, "r", encoding="utf-8") as file:
            for line in file:
                responses.append(json.loads(line))

        return responses

    def load(self):
        sources = self.load_sources()
        responses = self.load_responses()

        source_map = {
            source["source_id"]: source
            for source in sources
        }

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
                    "source": source["source"],
                    "source_info": source["source_info"],
                    "prompt": source["prompt"],
                    "response": response["response"],
                    "labels": response["labels"],
                })

        return dataset