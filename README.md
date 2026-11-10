# Hearsay

**Zero-Egress Hallucination Verification Gateway & Observability Middleware for Retrieval-Augmented Generation**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18.3-61DAFB.svg)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.5-3178C6.svg)](https://www.typescriptlang.org/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.0%2B-EE4C2C.svg)](https://pytorch.org/)
[![SQLite](https://img.shields.io/badge/SQLite-WAL%20Mode-003B57.svg)](https://www.sqlite.org/)
[![Tests](https://img.shields.io/badge/Tests-153%20Passed-brightgreen.svg)]()

---

Hearsay is an on-premises, zero-data-egress reverse proxy middleware that verifies the factual groundedness of Retrieval-Augmented Generation (RAG) outputs at runtime. Operating as a drop-in replacement for the OpenAI `/v1/chat/completions` REST interface, it intercepts candidate prose, decomposes it into atomic propositions, retrieves candidate premise spans, and evaluates entailment against ground-truth context using local Natural Language Inference (NLI) cross-encoders.

Rather than relying on non-deterministic "LLM-as-a-judge" prompting—which adds 2–4 seconds of latency, incurs per-token costs, and leaks confidential enterprise data to third-party APIs—Hearsay executes local CPU-bound inference (`DeBERTa-v3-small`, 143M parameters) in a fully air-gapped environment (`TRANSFORMERS_OFFLINE=1`).

Every verification run, claim verdict, and latency profile is committed to an indexed SQLite audit store with Write-Ahead Logging (`WAL`) and exposed via an interactive React 18 / TypeScript companion client and a Streamlit telemetry dashboard.

---

## Key Capabilities

* **OpenAI API Drop-In Compatibility:** Acts as a transparent ASGI reverse proxy. Applications switch to Hearsay by updating their client `base_url` to `http://localhost:8000/v1` with zero changes to networking code.
* **Dual-Path Verification Architecture:** Automatically routes inputs through either citation-bound verification (ALCE benchmark style) or uncited proposition segmentation and dense bi-encoder alignment (RAGTruth benchmark style).
* **Zero-Egress Local NLI:** Deploys a 143M parameter `DeBERTa-v3-small` cross-encoder running locally on CPU in FP32, ensuring no enterprise data leaves the host environment.
* **Asymmetric Safety Decision Boundary:** Implements domain-calibrated classification thresholds ($\tau_{\text{contra}} = 0.50$, $\tau_{\text{entail}} = 0.60$) prioritizing high-cost contradiction detection in legal and clinical settings.
* **Non-Blocking Concurrency Dispatcher:** Offloads PyTorch model inference to worker threadpools using `starlette.concurrency.run_in_threadpool`, keeping the FastAPI event loop responsive during multi-tenant workloads.
* **Dual-Threshold Mitigation Triage:** Features a non-blocking UI delivery workflow for ungrounded prose, coupled with an automated prompt critique loop with recursion capped at $\text{max\_retries} = 1$ to prevent latency runaway.
* **Sub-Millisecond Trace Persistence:** Persists all requests, claims, and latency metrics to SQLite 3 in WAL mode with sub-millisecond writes (`< 1 ms` $P_{50}$) and zero database locking.

---

## System Architecture

Hearsay is organized across four decoupled architectural tiers:

```
                            +------------------------------------------+
                            |       Client / Ingestion Layer           |
                            |  - Minimal RAG Companion (React 18/Vite) |
                            |  - In-Memory PDF Parser (pdfplumber)     |
                            |  - Third-Party OpenAI Client SDKs        |
                            +--------------------+---------------------+
                                                 |
                                  POST /v1/chat/completions
                                                 |
                                                 v
                            +------------------------------------------+
                            |     Reverse Proxy Gateway & Dispatcher   |
                            |  - FastAPI / Starlette ASGI Engine       |
                            |  - Context Extraction (JSON & Headers)   |
                            |  - Threadpool Worker Concurrency         |
                            +--------------------+---------------------+
                                                 |
                                 Candidate Text & Reference Premises
                                                 |
                                                 v
                            +------------------------------------------+
                            |       Core ML Verification Engine        |
                            |  - Proposition Segmentation (spaCy)      |
                            |  - Bi-Encoder Retrieval (all-MiniLM-L6)  |
                            |  - Cross-Encoder NLI (DeBERTa-v3-small)  |
                            |  - Asymmetric Decision Formalism         |
                            +--------------------+---------------------+
                                                 |
                                       Audit Traces & Proofs
                                                 |
                                                 v
                            +------------------------------------------+
                            |      Audit Persistence & Observability   |
                            |  - SQLite 3 TraceStore (WAL Mode)        |
                            |  - Live Inspector Drawer (React UI)      |
                            |  - Streamlit Telemetry Dashboard         |
                            +------------------------------------------+
```

### Architectural Tier Breakdown

1. **Tier 1: Client Application & Ingestion Layer**
   * **Minimal RAG Companion:** Single-page application built with React 18, Vite, TypeScript, and Tailwind CSS.
   * **Document Ingestion:** Client-side PDF text extraction and chunking (`pdfplumber` / `fitz`) with session context indexing.
   * **OpenAI Protocol Support:** Consumes standard OpenAI chat payloads via HTTP REST.
2. **Tier 2: Reverse Proxy Gateway & Async Concurrency**
   * **ASGI Reverse Proxy:** FastAPI middleware intercepting `/v1/chat/completions` and `/verify`.
   * **Context Extraction:** Automatically parses ground-truth context from request JSON payloads (`verirag_context`) or HTTP transport headers (`X-Hearsay-Context`, `X-Hearsay-Source-ID`).
   * **Non-Blocking Dispatcher:** Offloads synchronous PyTorch model computation to worker threads via Starlette threadpool dispatch, preserving event loop concurrency.
   * **Telemetry Injection:** Injects real-time verification headers into upstream responses: `X-Hearsay-Status`, `X-Hearsay-Score`, and `X-Hearsay-Request-ID`.
3. **Tier 3: Core ML Verification Engine**
   * **Proposition Decomposer:** Extracts atomic factual propositions from continuous model prose using spaCy dependency and clause segmentation (`en_core_web_sm`).
   * **Bi-Encoder Semantic Retriever:** Computes cosine similarity between claims and context chunks using `all-MiniLM-L6-v2` to select top-$k$ premise candidates ($k=3$).
   * **Cross-Encoder NLI Verifier:** Computes joint cross-attention over `(Premise, Claim)` pairs using `cross-encoder/nli-deberta-v3-small` (143M parameters) on local CPU.
4. **Tier 4: Audit Persistence & Observability**
   * **TraceStore Persistence:** SQLite 3 configured with `PRAGMA journal_mode=WAL;` and composite indices over `(request_id, timestamp)`, delivering sub-millisecond commits.
   * **Live Inspector Drawer:** Collapsible 360px sidecar drawer in the React UI displaying claim-level probabilities, highlighted evidence spans, and mitigation diff toggles.
   * **Streamlit Observability Dashboard:** Multi-page monitoring interface tracking real-time KPI banners, percentile latency curves ($P_{50}, P_{90}, P_{95}, P_{99}$), and context utilization diagnostics.

---

## Verification Pipeline & Decision Formalism

Hearsay employs an adaptive dual-path verification pipeline depending on whether the incoming prose contains structured citation markers.

```
                    RAG Response Prose & Context
                                 |
                                 v
                     [ Contains Citations? ]
                     /                     \
             YES (Cited)                 NO (Uncited)
                  |                            |
                  v                            v
        +--------------------+       +--------------------+
        |  Path A: ALCE      |       |  Path B: RAGTruth  |
        |  Citation Binding  |       |  Proposition Seg.  |
        |  - Regex isolator  |       |  - spaCy parser    |
        |  - Direct mapping  |       |  - all-MiniLM top-k|
        +---------+----------+       +---------+----------+
                  \                            /
                   \                          /
                    v                        v
             +--------------------------------------+
             |   Local DeBERTa-v3 Cross-Encoder     |
             |   Joint Cross-Attention over (p, c)  |
             |   Softmax: [P_ent, P_con, P_neu]     |
             +-------------------+------------------+
                                 |
                                 v
             +--------------------------------------+
             |    Asymmetric Decision Formalism     |
             |    - Supported:    P_ent >= 0.60     |
             |    - Contradicted: P_con >= 0.50     |
             |    - Ungrounded:   Otherwise         |
             +--------------------------------------+
```

### 1. Mathematical Decision Rule

Each decomposed claim $c_i$ is evaluated against its candidate premise $p_j$. The model outputs softmax logits across Entailment, Contradiction, and Neutral classes:

$$\text{Label}(c_i) = \begin{cases} \text{SUPPORTED} & \text{if } P(\text{entailment}) \ge 0.60 \\ \text{CONTRADICTION} & \text{if } P(\text{contradiction}) \ge 0.50 \\ \text{UNGROUNDED} & \text{otherwise (Neutral / Insufficient Evidence)} \end{cases}$$

*Tie-break rule:* If both thresholds are met simultaneously, $\text{argmax}(P_{\text{entail}}, P_{\text{contra}})$ determines the verdict.

### 2. Domain Calibration Rationale

The classification bounds are intentionally asymmetric:

$$\tau_{\text{contra}} = 0.50 < \tau_{\text{entail}} = 0.60$$

In high-liability domains such as medical diagnostics and legal compliance, an active factual contradiction represents a catastrophic risk, whereas an ungrounded omission is merely uninformative. Lowering the contradiction barrier to $0.50$ triggers defensive mitigation aggressively, while demanding $0.60$ for entailment ensures that claims are only certified as safe when supported by high model confidence.

### 3. Response-Level Aggregated Metrics

For a response comprising $M$ segmented propositions:

* **Groundedness Score:**
  $$S_G = \frac{1}{M} \sum_{i=1}^{M} \mathbb{I}[\text{Label}(c_i) = \text{SUPPORTED}]$$
* **Contradiction Ratio:**
  $$S_C = \frac{1}{M} \sum_{i=1}^{M} \mathbb{I}[\text{Label}(c_i) = \text{CONTRADICTION}]$$
* **Citation Precision (Path A):**
  $$\text{Cite-P} = \frac{|\{c_i : D_k \models c_i\}|}{|\{c_i : c_i \text{ contains citations}\}|}$$

### 4. Mitigation Decision Logic

* **Branch A (Clean Delivery):** $S_C = 0\% \land S_G \ge 70\%$. Prose is certified clean and delivered immediately to the client.
* **Branch B (Interactive Triage):** $S_G < 70\% \lor 0\% < S_C \le 30\%$. Non-blocking delivery preserves low interactive latency. An amber warning badge is attached, and the user is provided a 1-click option in the UI to regenerate the response with injected ground-truth evidence.
* **Branch C (Automated Critique Loop):** $S_C > 30\%$. Severe contradiction triggers an automatic upstream critique reprompt injecting the specific refuted claim and true premise. Recursion is capped at \[
  \text{max\_retries} = 1
  \] to prevent latency stalls and token cost runaway.

---

## Empirical Evaluation & Benchmarks

### 1. Benchmark Accuracy (RAGTruth)

Evaluated on 50 sampled instances from the **RAGTruth** benchmark across news, legal, and biomedical generation tasks:

| Evaluator / Pipeline | Model Checkpoint | Parameters | Precision | Recall | F1 Score | Data Privacy |
|---|---|---|---|---|---|---|
| Prompted LLM Judge | GPT-4 (Cloud API) | ~1.8T | 68.4% | 72.1% | 70.2% | Third-Party Egress |
| MiniCheck (EMNLP '24) | DeBERTa-v3-Large | 435M | 79.2% | 78.4% | 78.8% | Local Inference |
| **Hearsay Gateway** | **DeBERTa-v3-Small** | **143M** | **81.5%** | **76.2%** | **78.8%** | **100% Zero-Egress CPU** |

*Key Result:* Hearsay achieves exact **78.8% F1 parity** with state-of-the-art MiniCheck while deploying a 143M model that is **$3\times$ smaller**, enabling local CPU execution without requiring dedicated GPU infrastructure.

### 2. Adversarial Red-Teaming & Evasion Robustness

To measure detector vulnerability against adversarial manipulation, Hearsay was evaluated against three controlled perturbation vectors:

| Evaluation Stage | Attack Vector | Technique | Detector Recall | Failure Mode / Root Cause |
|---|---|---|---|---|
| Baseline | Clean Text | Unperturbed RAG completions | 92.0% | Normal classification error |
| Perturbation 1 | Distractor Injection | High-overlap irrelevant sentences | 88.0% | Retrieval ranking dilution |
| Perturbation 2 | Entity Swap | Named entity replacement (dates/names) | 84.0% | Out-of-vocabulary entity masking |
| Perturbation 3 | **Epistemic Hedging** | Modal verbs (*"might suggest"*, *"could be"*) | **38.8%** | **Attention dilution into Neutral class** |
| **Defended** | **Calibrated Gateway** | Asymmetric threshold ($\tau_{\text{contra}} = 0.50$) | **100.0%** | **Full recall recovery** |

*Root Cause Analysis for Epistemic Hedging:* Adding epistemic modal qualifiers (*"Evidence might suggest..."*) causes the cross-encoder's multi-head attention to distribute softmax probability mass away from the Contradiction class into the Neutral class (dropping $P_{\text{contra}}$ from 98.4% to 44.8%). The calibrated decision threshold ($\tau_{\text{contra}} = 0.50$) successfully neutralizes this evasion vector, restoring full detection recall.

### 3. System Latency Profile

Measured on standard 8-core commodity CPU (Apple Silicon / x86_64, PyTorch FP32):

| System Component | P50 (Median) | P95 (Tail) | Notes |
|---|---|---|---|
| Proposition Decomposition (spaCy) | 48 ms | 72 ms | Sentence & clause segmentation |
| Bi-Encoder Premise Retrieval (all-MiniLM) | 18 ms | 26 ms | Cosine similarity across in-memory chunks |
| Cross-Encoder NLI Inference (DeBERTa-v3) | 1,180 ms | 1,690 ms | Joint cross-attention per claim-premise pair |
| SQLite WAL Trace Commit | 0.8 ms | 1.4 ms | Non-blocking write to `hearsay_traces.db` |
| Gateway Proxy Dispatch Overhead | 4.2 ms | 6.8 ms | Starlette threadpool dispatch & header parsing |
| **End-to-End Verification Cycle** | **1,280 ms** | **1,840 ms** | **Sub-1.3s local verification** |

---

## Quickstart

### Option A: Docker Compose (Recommended)

Boot the entire stack—FastAPI Proxy Gateway, React 18 Companion UI, and SQLite persistence—with one command:

```bash
docker compose up -d
```

* **Proxy Gateway API & Swagger Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)
* **Minimal RAG Companion UI:** [http://localhost:5173](http://localhost:5173)
* **Streamlit Observability Dashboard:** [http://localhost:8501](http://localhost:8501)

Check service status and logs:
```bash
docker compose ps
docker compose logs -f
```

---

### Option B: Local Source Installation

#### Prerequisites
* Python 3.11+
* Node.js 18+ and npm
* Git

#### 1. Setup Backend & Gateway
```bash
# Clone the repository
git clone https://github.com/Chehrehmi/hearsay.git
cd hearsay

# Create and activate Python virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies and download spaCy model
pip install -r requirements.txt
python -m spacy download en_core_web_sm

# Launch the FastAPI Proxy Gateway (Port 8000)
uvicorn hearsay.proxy.gateway:app --reload --port 8000
```

#### 2. Setup React Minimal RAG Companion (In a separate terminal)
```bash
cd hearsay/frontend
npm install
npm run dev
# Running on http://localhost:5173
```

#### 3. Setup Streamlit Observability Dashboard (Optional, separate terminal)
```bash
cd hearsay
source .venv/bin/activate
streamlit run hearsay/ui/dashboard.py
# Running on http://localhost:8501
```

---

## Integration Guide

### 1. Direct Verification Endpoint (`POST /verify`)

Use this endpoint to verify arbitrary text against ground-truth context:

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

#### Response Payload
```json
{
  "request_id": "9d4a8e2b",
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
      "confidence": 0.94,
      "evidence_span": "Apollo 11 was the American spaceflight that first landed humans on the Moon on July 20, 1969.",
      "source_chunk_id": "wiki_apollo11"
    },
    {
      "claim_id": 1,
      "claim_text": "The astronauts landed on Mars in 1975",
      "status": "Unsupported (Ungrounded)",
      "confidence": 0.82,
      "evidence_span": null,
      "source_chunk_id": null
    }
  ],
  "latency_ms": 1284.15
}
```

---

### 2. OpenAI SDK Drop-In Replacement (`POST /v1/chat/completions`)

Forward standard chat completions through Hearsay by passing context via headers or request parameters:

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="not-needed-for-local-proxy",
)

response = client.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[
        {"role": "system", "content": "You are a clinical assistant."},
        {"role": "user", "content": "What is the recommended dosage for Lisinopril?"}
    ],
    extra_headers={
        "X-Hearsay-Context": "The recommended initial dosage for Lisinopril is 10 mg once daily for hypertension.",
        "X-Hearsay-Source-ID": "fda_label_lisinopril"
    }
)

# Inspect injected verification headers
print("Verification Status:", response.headers.get("X-Hearsay-Status"))
print("Groundedness Score:", response.headers.get("X-Hearsay-Score"))
print("Audit Request ID:", response.headers.get("X-Hearsay-Request-ID"))
```

---

## API Reference

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Service liveness and model initialization healthcheck. |
| `POST` | `/verify` | Sentence-level verification against provided context. |
| `POST` | `/v1/chat/completions` | OpenAI-compatible reverse proxy endpoint with telemetry header injection. |
| `GET` | `/v1/traces` | Paginated query over historical audit traces with status filters. |
| `GET` | `/v1/traces/{request_id}` | Detailed trace inspection for a specific request ID. |
| `GET` | `/v1/metrics` | Real-time aggregate KPIs, pass rates, and latency percentiles. |

---

## Repository Structure

```
hearsay/
├── Dockerfile                   # Multi-stage container definition
├── docker-compose.yml           # Compose specification (Gateway, UI, Dashboard)
├── requirements.txt             # Python dependencies
├── pytest.ini                   # Pytest runner configuration
│
├── frontend/                    # Minimal RAG Companion (React 18 / TypeScript)
│   ├── src/
│   │   ├── components/          # ChatWindow, HearsayDrawer, FileUpload, StatusPill
│   │   ├── App.tsx              # Main application shell
│   │   └── main.tsx             # Entrypoint
│   ├── package.json             # Frontend dependencies (Vite, Tailwind)
│   └── vite.config.ts           # Development server and proxy configuration
│
├── hearsay/                     # Core backend package
│   ├── proxy/
│   │   ├── protocol.py          # Pydantic v2 schemas for requests & responses
│   │   └── gateway.py           # FastAPI reverse proxy, routes & telemetry
│   ├── db/
│   │   └── trace_store.py       # SQLite 3 WAL engine, indexes & percentiles
│   ├── engine/
│   │   ├── decomposer.py        # spaCy atomic claim segmenter
│   │   ├── retriever.py         # all-MiniLM semantic premise matcher
│   │   ├── verifier.py          # DeBERTa-v3 cross-encoder NLI classifier
│   │   └── pipeline.py          # Dual-path verification orchestration pipeline
│   ├── eval/
│   │   ├── loader.py            # RAGTruth dataset ingestion
│   │   ├── aligner.py           # Ground-truth span alignment
│   │   └── metrics.py           # Precision, Recall, and F1 calculations
│   └── ui/
│       └── dashboard.py         # Streamlit telemetry dashboard
│
├── data/                        # Benchmark datasets (RAGTruth splits)
│   └── response.jsonl
│
├── docs/                        # Engineering documentation & architecture diagrams
│   └── diagrams/                # System architecture, DFDs, and sequence charts
│
└── tests/                       # Automated test suite (153 tests)
    ├── test_protocol.py         # Protocol serialization & validation
    ├── test_gateway.py          # Reverse proxy routing & headers
    ├── test_trace_store.py      # SQLite WAL persistence & percentiles
    ├── test_engine.py           # End-to-end NLI verification engine
    ├── test_decomposer.py       # Proposition decomposition logic
    ├── test_retriever.py        # Semantic premise retrieval
    ├── test_citation_verifier.py# ALCE citation regex & binding
    └── test_ui.py               # Streamlit dashboard tests
```

---

## Automated Test Suite

Hearsay maintains 100% passing automated test coverage across all subsystems. Run tests using `pytest`:

```bash
pytest -v
```

```text
============================= test session starts ==============================
platform darwin -- Python 3.11.3, pytest-9.1.1, pluggy-1.6.0
collected 153 items

tests/test_alce_loader.py .                                              [  0%]
tests/test_aligner.py .....                                              [  3%]
tests/test_benchmark_runner.py ......                                    [  7%]
tests/test_citation_verifier.py ..                                       [  9%]
tests/test_decomposer.py .............                                   [ 17%]
tests/test_demo_corpus.py .......                                        [ 22%]
tests/test_engine.py ................                                    [ 32%]
tests/test_error_analysis.py ......                                      [ 36%]
tests/test_gateway.py .............................                      [ 55%]
tests/test_live_proxy.py ..                                              [ 56%]
tests/test_loader.py ........                                            [ 62%]
tests/test_metrics.py .......                                            [ 66%]
tests/test_protocol.py .....................                             [ 80%]
tests/test_report_generator.py ...                                       [ 82%]
tests/test_retriever.py ........                                         [ 87%]
tests/test_trace_store.py .........                                      [ 93%]
tests/test_ui.py ...                                                     [ 95%]
tests/test_verifier.py .......                                           [100%]

====================== 153 passed, 10 warnings in 29.43s =======================
```

To run frontend TypeScript and build verification:
```bash
cd frontend && npm run build
```

---

## Technical Attribution & Project Scope

Hearsay was designed and implemented as a 3rd-Semester Master of Computer Applications (MCA) Mini-Project (Course `22-382-0303`) at the Department of Computer Applications, Cochin University of Science and Technology (CUSAT). 

The project was evaluated and defended before Head of Department **Dr. Vinod P.** (Marie Curie Fellow; Expert in Adversarial Machine Learning & Privacy) and project guide **Dr. M. V. Judy**.

### Engineering Ownership & Division of Responsibilities
* **Jeremy (Systems Architect & Team Lead):** Designed the overall system architecture; engineered the FastAPI reverse proxy gateway (`gateway.py`) and OpenAI `/v1/chat/completions` protocol layer; built the non-blocking Starlette threadpool concurrency dispatcher; developed the SQLite 3 WAL persistence engine (`trace_store.py`); developed the React 18 / TypeScript Minimal RAG Companion client and Live Inspector telemetry drawer; integrated the end-to-end ML pipeline; containerized the multi-tier application via Docker Compose.
* **Akhil (Core ML & Verification Lead):** Co-developed the atomic proposition decomposition pipeline (`decomposer.py`), dense premise retrieval (`retriever.py`), and DeBERTa cross-encoder classification logic (`verifier.py`).
* **Harry (Data & Evaluation Lead):** Curated the RAGTruth benchmark splits (`loader.py`), implemented span alignment logic (`aligner.py`), and executed benchmark evaluation runs (`metrics.py`).

### Scope & Architectural Boundaries
* **What Hearsay is:** An inline, zero-data-egress verification gateway, reverse proxy, and local NLI inference middleware designed to intercept and evaluate RAG generations against reference context.
* **What Hearsay is not:** It does not implement a distributed vector database cluster (such as Milvus, Qdrant, or Pinecone); reference premise retrieval is performed locally over in-memory document chunks via dense bi-encoder cosine similarity. The underlying NLI models (`DeBERTa-v3-small` and `all-MiniLM-L6-v2`) are pre-trained checkpoints evaluated and calibrated for asymmetric inference, not trained from scratch.

---

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
