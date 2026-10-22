# Hearsay

**Runtime Groundedness Verification Gateway & Observability Middleware for Retrieval-Augmented Generation (RAG)**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.40%2B-FF4B4B.svg)](https://streamlit.io/)
[![Docker](https://img.shields.io/badge/Docker-Compose%20v2-2496ED.svg)](https://www.docker.com/)
[![Tests](https://img.shields.io/badge/Tests-86%20Passed-brightgreen.svg)]()

---

Hearsay is an open-source, OpenAI-compatible reverse proxy middleware that verifies the factual groundedness of RAG responses in real time. Rather than relying on expensive, non-deterministic "LLM-as-a-judge" evaluation calls, Hearsay runs a deterministic sentence-level pipeline: it splits model-generated prose into atomic propositions, retrieves candidate evidence spans, and computes Natural Language Inference (NLI) entailment scores locally.

Every verification request, claim verdict, and latency profile is persisted to an indexed SQLite audit store and visualized in an interactive observability dashboard.

---

## Architecture Overview

```
                      ┌──────────────────────────────────────┐
                      │          Incoming RAG Client         │
                      │  (OpenAI SDK, LangChain, LlamaIndex) │
                      └──────────────────┬───────────────────┘
                                         │
                   POST /v1/chat/completions or POST /verify
                                         │
                                         ▼
┌───────────────────────────────────────────────────────────────────────────────────┐
│                                 HEARSAY GATEWAY                                   │
│                                                                                   │
│   • OpenAI Protocol Compatibility Layer                                           │
│   • Context Extraction (Request Body & X-Hearsay-Context Headers)                  │
│   • Real-Time Telemetry Header Injection (X-Hearsay-Status, X-Hearsay-Score)     │
└─────────────────┬─────────────────────────────────────────────────▲───────────────┘
                  │                                                 │
                  ▼                                                 │
┌──────────────────────────────────────────────────┐                │
│             CORE VERIFICATION ENGINE             │                │
│                                                  │                │
│  1. Claim Decomposition                          │                │
│     Extracts atomic claims via spaCy clause      │                │
│     and sentence segmentation                    │                │
│                  │                               │                │
│                  ▼                               │                │
│  2. Bi-Encoder Semantic Retrieval                │                │
│     Locates candidate evidence spans             │                │
│     using all-MiniLM-L6-v2 vector similarity     │                │
│                  │                               │                │
│                  ▼                               │                │
│  3. Local NLI Cross-Encoder Classification       │                │
│     Computes entailment/contradiction logits     │                │
│     via cross-encoder/nli-deberta-v3-small       │                │
│                  │                               │                │
│                  ▼                               │                │
│  4. Verdict Assignment & Groundedness Scoring    │                │
│     • Supported (Entailment >= 0.60)             │                │
│     • Contradicted (Contradiction >= 0.50)       │                │
│     • Ungrounded (Insufficient Evidence)         │                │
└─────────────────┬────────────────────────────────┘                │
                  │                                                 │
                  ▼                                                 │
┌──────────────────────────────────────────────────┐                │
│           SQLITE AUDIT STORE (TraceStore)        │                │
│                                                  │                │
│  • Indexed by timestamp DESC and overall_status  │                │
│  • P50, P90, P95, and P99 Latency Percentiles    │                │
│  • Full claim-to-evidence JSON serialization     │────────────────┘
└─────────────────┬────────────────────────────────┘
                  │
                  ▼
┌───────────────────────────────────────────────────────────────────────────────────┐
│                       STREAMLIT OBSERVABILITY DASHBOARD                           │
│                                                                                   │
│   • Real-Time Telemetry KPI Banner (Pass Rate, Groundedness %, P50/P95 Latency)   │
│   • Trace Explorer with Color-Coded Evidence Cards (🟢 / 🟡 / 🔴)                  │
│   • Retrieval Diagnostics & Context Utilization Rate Warnings                     │
│   • Interactive Live Verification Playground & Sandbox                            │
└───────────────────────────────────────────────────────────────────────────────────┘
```

---

## Quickstart

### 1. Run with Docker Compose (Recommended)

The entire system—including the proxy gateway and observability UI—boots with a single command:

```bash
docker compose up -d
```

- **Gateway API & Swagger Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Streamlit Observability Dashboard:** [http://localhost:8501](http://localhost:8501)

To view running containers and logs:
```bash
docker compose ps
docker compose logs -f
```

To shut down:
```bash
docker compose down
```

---

### 2. Run Locally from Source

#### Prerequisites
- Python 3.11+
- Virtual environment tool (`venv` or `conda`)

```bash
# Clone repository
git clone https://github.com/Chehrehmi/hearsay.git
cd hearsay

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies and download spaCy NLP model
pip install -r requirements.txt
python -m spacy download en_core_web_sm

# Launch the FastAPI Proxy Gateway (Port 8000)
uvicorn hearsay.proxy.gateway:app --reload --port 8000

# In a separate terminal, launch the Streamlit Dashboard (Port 8501)
streamlit run hearsay/ui/dashboard.py
```

---

## API Reference

### Core Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Liveness healthcheck endpoint. |
| `POST` | `/verify` | Direct sentence-level verification against provided context. |
| `POST` | `/v1/chat/completions` | OpenAI-compatible proxy endpoint with telemetry headers. |
| `GET` | `/v1/traces` | Paginated audit trace logs with status filtering. |
| `GET` | `/v1/traces/{request_id}` | Detailed trace inspection for a specific request. |
| `GET` | `/v1/metrics` | Real-time aggregate KPIs, pass rates, and P50/P95 latency. |

---

### Verification Example (`POST /verify`)

#### Request
```bash
curl -X POST http://localhost:8000/verify \
  -H "Content-Type: application/json" \
  -d '{
    "response_text": "Apollo 11 landed on the Moon in 1969. The astronauts landed on Mars in 1975.",
    "verirag_context": {
      "source_id": "wiki_apollo11",
      "source_info": "Apollo 11 was the American spaceflight that first landed humans on the Moon on July 20, 1969."
    }
  }'
```

#### Response
```json
{
  "request_id": "e4b9c1a0",
  "overall_status": "Hallucination Detected",
  "groundedness_score": 50.0,
  "total_claims": 2,
  "supported_claims": 1,
  "contradicted_claims": 0,
  "ungrounded_claims": 1,
  "claims": [
    {
      "claim_id": 0,
      "claim_text": "Apollo 11 landed on the Moon in 1969",
      "status": "Supported",
      "confidence": 0.95,
      "evidence_span": "Apollo 11 was the American spaceflight that first landed humans on the Moon on July 20, 1969.",
      "source_chunk_id": "wiki_apollo11"
    },
    {
      "claim_id": 1,
      "claim_text": "The astronauts landed on Mars in 1975",
      "status": "Unsupported (Ungrounded)",
      "confidence": 0.80,
      "evidence_span": null,
      "source_chunk_id": null
    }
  ],
  "latency_ms": 14.82
}
```

---

### OpenAI-Compatible Proxy (`POST /v1/chat/completions`)

Clients can forward existing OpenAI chat completion requests directly to Hearsay by supplying context via the body payload (`verirag_context`) or HTTP headers (`X-Hearsay-Context`, `X-Hearsay-Source-ID`):

```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "X-Hearsay-Context: Water freezes at 0 degrees Celsius under standard atmospheric pressure." \
  -H "X-Hearsay-Source-ID: doc_physics_01" \
  -d '{
    "model": "gpt-3.5-turbo",
    "messages": [
      {"role": "user", "content": "At what temperature does water freeze?"}
    ],
    "response_text": "Water freezes at 0 degrees Celsius."
  }'
```

#### Injected HTTP Response Headers
```http
HTTP/1.1 200 OK
X-Hearsay-Status: Verified
X-Hearsay-Score: 100.0
X-Hearsay-Request-ID: a7f82c19
Content-Type: application/json
```

---

## Observability Dashboard

The Streamlit UI (`hearsay/ui/dashboard.py`) provides end-to-end visibility into verification operations:

- **Telemetry Banner:** Real-time KPI cards tracking Total Requests, Verification Pass Rate, Average Groundedness Score, P50 Latency (median), P95 Latency (tail), and Hallucinations Caught.
- **Trace Explorer:** Interactive inspection of historical verification runs with status filtering (`All`, `Verified`, `Hallucination Detected`), full generated text review, and color-coded claim breakdown cards:
  - 🟢 **Supported** (with linked evidence span)
  - 🟡 **Ungrounded** (highlighting unsupported claims)
  - 🔴 **Contradiction** (flagging contradictory statements)
- **Retrieval Diagnostics:** Automatically measures Context Utilization Rate and generates warnings if retrieved document chunks fail to ground generated claims.
- **Live Verification Sandbox:** Interactive playground allowing developers to paste custom reference documents and LLM outputs to inspect real-time grounding verdicts before deployment.
- **Latency Analytics:** Request latency trend chart over time and percentile distribution profile (P50, P90, P95, P99).

---

## Project Structure

```
hearsay/
├── Dockerfile                   # Production Python 3.11 container definition
├── docker-compose.yml           # Multi-service composition (Gateway + Dashboard)
├── .dockerignore                # Build exclusions
├── requirements.txt             # Locked project dependencies
├── pytest.ini                   # Pytest path and runner configuration
│
├── hearsay/                     # Core application package
│   ├── proxy/                   # Reverse proxy gateway & protocol
│   │   ├── protocol.py          # Pydantic v2 request/response schemas
│   │   └── gateway.py           # FastAPI proxy middleware & observability endpoints
│   ├── db/                      # Audit storage & telemetry
│   │   └── trace_store.py       # SQLite engine, indexes & percentile analytics
│   ├── engine/                  # Core NLP verification pipeline
│   │   ├── decomposer.py        # spaCy atomic claim segmenter
│   │   ├── retriever.py         # Bi-encoder semantic candidate matcher
│   │   └── pipeline.py          # HearsayEngine orchestration pipeline
│   ├── eval/                    # Benchmarking & evaluation
│   │   ├── metrics.py           # Precision, Recall, and F1 calculations
│   │   └── aligner.py           # Ground-truth span alignment
│   └── ui/                      # Observability dashboard
│       └── dashboard.py         # Streamlit telemetry interface & live sandbox
│
├── data/                        # Benchmark datasets (RAGTruth samples)
│   └── response.jsonl
│
└── tests/                       # Automated test suite (86 tests)
    ├── test_protocol.py         # Protocol validation & schema serialization
    ├── test_gateway.py          # API gateway endpoints & header parsing
    ├── test_trace_store.py      # SQLite CRUD, percentiles & aggregations
    ├── test_ui.py               # Headless Streamlit rendering & KPI tests
    ├── test_decomposer.py       # Sentence decomposition tests
    ├── test_retriever.py        # Semantic ranking & score tests
    ├── test_aligner.py          # Span alignment tests
    ├── test_loader.py           # Dataset loading tests
    └── test_metrics.py          # Precision/Recall metric tests
```

---

## Automated Test Suite

Hearsay maintains strict test coverage across all subsystems. Run tests using `pytest`:

```bash
pytest -v
```

All 86 test cases run against isolated SQLite temporary fixtures and headless Streamlit environments, ensuring no state pollution:

```text
============================== 86 passed in 30.43s ==============================
```

---

## Team & Agile Division of Responsibilities

Developed as part of the 1-Week Agile MVP Plan for RAG Groundedness Verification:

- **Jeremy (Lead Architect & Full-Stack Lead):** Reverse proxy gateway (`gateway.py`), Pydantic protocol (`protocol.py`), SQLite audit store (`trace_store.py`), Streamlit observability dashboard (`dashboard.py`), and Docker containerization.
- **Akhil (Core ML & Verification Lead):** Atomic claim decomposition (`decomposer.py`), bi-encoder retrieval (`retriever.py`), and DeBERTa cross-encoder NLI verification (`pipeline.py`).
- **Harry (Data & Evaluation Lead):** RAGTruth dataset ingestion (`loader.py`), ground-truth span alignment (`aligner.py`), and evaluation benchmark harness (`metrics.py`).

---

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
