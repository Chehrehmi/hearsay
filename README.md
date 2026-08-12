# 🛡️ Hearsay (formerly VeriRAG)

> **Runtime Groundedness Verification Gateway & Observability Middleware for Retrieval-Augmented Generation (RAG)**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![HuggingFace](https://img.shields.io/badge/%F0%9F%A4%97-HuggingFace-orange)](https://huggingface.co/)

---

## 📌 Executive Summary

**Hearsay** is a self-hosted, OpenAI-compatible runtime verification reverse-proxy middleware designed to intercept RAG responses, decompose generated outputs into discrete atomic claims, and verify each claim against retrieved document evidence using lightweight local Natural Language Inference (NLI) models (`cross-encoder/nli-deberta-v3-small`).

For our 1-Week Agile MVP, Hearsay focuses on **Path B: Sentence-Level Groundedness Verification of Uncited Prose**, benchmarked directly against the **RAGTruth** corpus (ACL 2024).

```
┌───────────────────────────────────────────────────────────────────────────────────┐
|                                HEARSAY GATEWAY                                    |
|                                                                                   |
|  ┌────────────────────────────────────┐    ┌───────────────────────────────────┐  |
|  │ FastAPI OpenAI-Compatible Proxy    │    │ SQLite Audit & Trace Store        │  |
|  │ (/v1/chat/completions & /verify)   │    │ (hearsay_traces.db)               │  |
|  └─────────────────┬──────────────────┘    └─────────────────▲─────────────────┘  |
└────────────────────┼─────────────────────────────────────────┼────────────────────┘
                     │                                         │
                     ▼                                         │
┌──────────────────────────────────────────────────────────────┴────────────────────┐
|                           CORE VERIFICATION ENGINE                                |
|                                                                                   |
|  ┌───────────────────────────┐             ┌───────────────────────────────────┐  |
|  │ 1. Claim Decomposer       │             │ 3. Local DeBERTa Cross-Encoder    │  |
|  │    (spaCy / PySBD)        │             │    NLI Verification Engine        │  |
|  └─────────────┬─────────────┘             └─────────────────▲─────────────────┘  |
|                │                                             │                    |
|                ▼                                             │                    |
|  ┌───────────────────────────┐             ┌─────────────────┴─────────────────┐  |
|  │ 2. Bi-Encoder Retriever   ├────────────►│ 4. Verdict & Confidence Classifier│  |
|  │    (all-MiniLM-L6-v2)     │             │    (Supported/Contradicted/Ungnd) │  |
|  └───────────────────────────┘             └───────────────────────────────────┘  |
└───────────────────────────────────────────────────────────────────────────────────┘
                                         │
                                         ▼
┌──────────────────────────────────────────────────────────────┴────────────────────┐
|                        EVALUATION & OBSERVABILITY UI                              |
|                                                                                   |
|  ┌────────────────────────────────────┐    ┌───────────────────────────────────┐  |
|  │ RAGTruth Metric Evaluator          │    │ Streamlit Observability Dashboard │  |
|  │ (Precision, Recall, F1, Latency)   │    │ (Evidence Spans & Audit Logs)     │  |
|  └────────────────────────────────────┘    └───────────────────────────────────┘  |
└───────────────────────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Key Features (1-Week MVP Scope)

1. **OpenAI-Compatible Reverse Proxy:** Drop-in middleware that intercepts requests sent to `/v1/chat/completions` or direct `/verify` endpoints without breaking existing RAG client integrations.
2. **Rule-Based Claim Decomposition:** Splitting LLM natural prose into atomic propositions using spaCy dependency parsing & conjunction clause segmentation.
3. **Bi-Encoder Candidate Retrieval:** Rapid pre-filtering of retrieved context chunks using `all-MiniLM-L6-v2` vector similarity to locate target candidate spans.
4. **Local NLI Entailment Classification:** Scoring claims with `nli-deberta-v3-small` into continuous confidence bounds across 3 status labels:
   - 🟢 **Supported**: Claim is explicitly entailed by retrieved context chunk ($P(\text{entailment}) \ge 0.60$).
   - 🔴 **Unsupported (Contradiction)**: Claim directly contradicts retrieved chunk ($P(\text{contradiction}) \ge 0.50$).
   - 🟡 **Unsupported (Ungrounded)**: Claim introduces external/baseless information not present in retrieved context.
5. **RAGTruth Benchmark Harness:** Full evaluation pipeline computing Precision, Recall, F1, and Latency (P50/P95) across MS MARCO QA, CNN/DailyMail Summarization, and Yelp Data-to-Text tasks.
6. **Evidence-Linked Observability Dashboard:** Streamlit UI displaying side-by-side claim-to-evidence span highlighting, confidence pills, and retrieval diagnostic telemetry.

---

## 👥 Team & Agile Division of Labor

- **Akhil**: Core ML & Verification Engine (`hearsay/engine/`)
- **Harry**: Data Pipeline & RAGTruth Metric Evaluation (`hearsay/eval/`, `hearsay/dataset/`)
- **Jeremy**: Proxy Gateway, SQLite Trace DB & Observability UI (`hearsay/proxy/`, `hearsay/db/`, `hearsay/ui/`)

Full 7-day schedule and handbook available in [HEARSAY_1WEEK_MVP_AGILE_PLAN.md](HEARSAY_1WEEK_MVP_AGILE_PLAN.md).

---

## ⚙️ Quickstart Guide

### 1. Installation

```bash
# Clone the repository
git clone https://github.com/Chehrehmi/hearsay.git
cd hearsay

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies & spaCy language model
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

### 2. Launch Hearsay Gateway

```bash
# Start the FastAPI proxy gateway
uvicorn hearsay.proxy.gateway:app --reload --port 8000
```

### 3. Launch Observability Dashboard

```bash
# Launch Streamlit dashboard
streamlit run hearsay/ui/dashboard.py
```

### 4. Run RAGTruth Benchmark

```bash
# Run quantitative metrics evaluation over RAGTruth sample dataset
python -m hearsay.eval.benchmark_runner --dataset data/response.jsonl
```

---

## 📜 License

Distributed under the **MIT License**. See `LICENSE` for more information.
