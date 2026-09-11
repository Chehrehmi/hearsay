import json
import pytest
import pandas as pd
from pathlib import Path

from hearsay.dataset import RAGTruthLoader


@pytest.fixture
def mock_data_dir(tmp_path):
    """Creates a temporary data directory with sample RAGTruth JSONL files."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    sources = [
        {
            "source_id": 101,
            "source": "NASA announced Artemis program updates today.",
            "source_info": "NASA press release, Washington D.C.",
            "prompt": "What did NASA announce?",
            "task_type": "QA"
        },
        {
            "source_id": 102,
            "source": "Quantum computers use qubits rather than classical bits.",
            "source_info": "Quantum Computing 101 textbook.",
            "prompt": "Explain qubits.",
            # Note: task_type omitted to test fallback to 'Unknown'
        }
    ]

    responses = [
        {
            "id": 1,
            "source_id": 101,
            "model": "gpt-4",
            "temperature": 0.7,
            "split": "test",
            "quality": "good",
            "response": "NASA announced Artemis program updates today regarding lunar missions.",
            "labels": [{"start": 0, "end": 45, "label_type": "Supported"}]
        },
        {
            "id": 2,
            "source_id": 102,
            "model": "gpt-3.5-turbo",
            "temperature": 0.2,
            "split": "dev",
            "quality": "fair",
            "response": "Qubits are quantum bits that can exist in superposition.",
            "labels": []
        },
        {
            "id": 3,
            "source_id": 999,  # Unmatched source_id to test filtering
            "model": "llama-2",
            "temperature": 0.5,
            "split": "train",
            "quality": "poor",
            "response": "This response has no matching source.",
            "labels": []
        }
    ]

    source_file = data_dir / "source_info.jsonl"
    with open(source_file, "w", encoding="utf-8") as f:
        for s in sources:
            f.write(json.dumps(s) + "\n")
        f.write("\n")  # Blank line to test robust whitespace handling

    response_file = data_dir / "response.jsonl"
    with open(response_file, "w", encoding="utf-8") as f:
        for r in responses:
            f.write(json.dumps(r) + "\n")

    return data_dir


def test_loader_initialization():
    default_loader = RAGTruthLoader()
    assert default_loader.data_dir == Path("data")

    custom_loader = RAGTruthLoader(data_dir="/tmp/custom")
    assert custom_loader.data_dir == Path("/tmp/custom")


def test_dataset_package_export():
    from hearsay.dataset import RAGTruthLoader as ExportedLoader
    assert ExportedLoader is RAGTruthLoader


def test_load_sources_and_responses(mock_data_dir):
    loader = RAGTruthLoader(data_dir=mock_data_dir)
    sources = loader.load_sources()
    responses = loader.load_responses()

    assert len(sources) == 2
    assert sources[0]["source_id"] == 101
    assert sources[1]["source_id"] == 102

    assert len(responses) == 3
    assert responses[0]["id"] == 1
    assert responses[1]["id"] == 2
    assert responses[2]["id"] == 3


def test_load_joined_records(mock_data_dir):
    loader = RAGTruthLoader(data_dir=mock_data_dir)
    records = loader.load()

    # Response with source_id 999 should be excluded because it has no matching source
    assert len(records) == 2

    # Check first record mapping
    r1 = records[0]
    assert r1["id"] == 1
    assert r1["source_id"] == 101
    assert r1["model"] == "gpt-4"
    assert r1["temperature"] == 0.7
    assert r1["split"] == "test"
    assert r1["quality"] == "good"
    assert r1["task_type"] == "QA"
    assert r1["source"] == "NASA announced Artemis program updates today."
    assert r1["source_info"] == "NASA press release, Washington D.C."
    assert r1["prompt"] == "What did NASA announce?"
    assert "NASA announced Artemis" in r1["response"]
    assert len(r1["labels"]) == 1

    # Check second record fallback for missing task_type
    r2 = records[1]
    assert r2["id"] == 2
    assert r2["source_id"] == 102
    assert r2["task_type"] == "Unknown"


def test_load_joined_dataset_as_dataframe(mock_data_dir):
    loader = RAGTruthLoader(data_dir=mock_data_dir)
    df = loader.load_joined_dataset()

    assert isinstance(df, pd.DataFrame)
    assert len(df) == 2

    expected_columns = {
        "id", "source_id", "model", "temperature", "split", "quality",
        "task_type", "source", "source_info", "prompt", "response", "labels"
    }
    assert expected_columns.issubset(set(df.columns))
    assert df.iloc[0]["id"] == 1
    assert df.iloc[1]["id"] == 2


def test_load_as_dataframe_alias(mock_data_dir):
    loader = RAGTruthLoader(data_dir=mock_data_dir)
    df_primary = loader.load_joined_dataset()
    df_alias = loader.load_as_dataframe()

    assert isinstance(df_alias, pd.DataFrame)
    pd.testing.assert_frame_equal(df_primary, df_alias)


def test_missing_files_raises_error(tmp_path):
    empty_dir = tmp_path / "empty_dir"
    empty_dir.mkdir()

    loader = RAGTruthLoader(data_dir=empty_dir)
    with pytest.raises(FileNotFoundError):
        loader.load_sources()

    with pytest.raises(FileNotFoundError):
        loader.load_responses()


def test_real_data_smoke_test():
    """Lightweight smoke test on actual repository data/ directory if present."""
    data_path = Path("data")
    if (data_path / "source_info.jsonl").exists() and (data_path / "response.jsonl").exists():
        loader = RAGTruthLoader(data_dir=data_path)
        sources = loader.load_sources()
        assert len(sources) > 0, "source_info.jsonl should not be empty"

        responses = loader.load_responses()
        assert len(responses) > 0, "response.jsonl should not be empty"

        # Verify DataFrame conversion on first few rows
        joined = loader.load()
        assert len(joined) > 0
        df = loader.load_joined_dataset()
        assert isinstance(df, pd.DataFrame)
        assert len(df) == len(joined)
