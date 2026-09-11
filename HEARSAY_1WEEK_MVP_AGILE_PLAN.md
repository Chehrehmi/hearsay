# HEARSAY: 1-Week Agile MVP Sprint Plan & Team Handbook
## Path B: Sentence-Level Groundedness Verification of Uncited Prose on RAGTruth

> **Project Name:** Hearsay (formerly *VeriRAG*)  
> **Sprint Scope:** 1-Week MVP (7 Days, ~35 Hours / Person)  
> **Team Members (3 People):** Akhil, Harry, Jeremy  
> **Core Focus:** Path B — Uncited Prose Groundedness Verification benchmarked on RAGTruth Corpus (`source_info.jsonl` & `response.jsonl`)  
> **Agile Philosophy:** *Focus on one thing at a time, do it exceptionally well, show a working demo in 1 week, and iterate.*

---

## 1. Executive Summary & Sprint Goal

During our project guide meeting, the guide approved our transition to the **Agile development methodology**, accepted our official project name change to **Hearsay**, and requested a **working, high-quality MVP demo within 1 week**.

The guide emphasized:
> *"Focus on one thing at a time and do it well, and then increment and make it better."*

In accordance with this directive, we are focusing 100% of our 1-Week MVP on **Path B: Sentence-Level Groundedness Verification for Uncited Prose**. 

### What the MVP Will Do by Day 7:
1. Intercept a user prompt, retrieved document chunks (`source_info`), and an LLM-generated response (`response`).
2. Decompose the LLM response into discrete, atomic claims/sentences.
3. Retrieve candidate evidence spans from source chunks using a fast bi-encoder (`all-MiniLM-L6-v2`).
4. Perform local Natural Language Inference (NLI) using `cross-encoder/nli-deberta-v3-small` (or ONNX INT8) to label each claim as **Supported**, **Contradicted**, or **Ungrounded**, alongside a continuous confidence score.
5. Compute quantitative accuracy, precision, recall, F1, and latency metrics across the **RAGTruth** dataset.
6. Display an interactive **Evidence-Linked Observability Dashboard** with visual highlight spans, confidence pills, and audit logging.

---

## 2. System Architecture & Module Boundaries

```
┌───────────────────────────────────────────────────────────────────────────────────┐
|                                HEARSAY GATEWAY                                    |
|                                (Owner: Jeremy)                                    |
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
|                                (Owner: Akhil)                                     |
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
|                            (Owners: Harry & Jeremy)                               |
|                                                                                   |
|  ┌────────────────────────────────────┐    ┌───────────────────────────────────┐  |
|  │ RAGTruth Metric Evaluator (Harry)  │    │ Streamlit Observability Dashboard │  |
|  │ (Precision, Recall, F1, Latency)   │    │ (Jeremy - Evidence Spans & UI)    │  |
|  └────────────────────────────────────┘    └───────────────────────────────────┘  |
└───────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. GitHub Agile Workflow & Branching Strategy

To operate like a professional software team, all 3 members must strictly follow our GitHub workflow protocol.

```
                          ┌──────────────────────────┐
                          │   main (Stable / Demo)   │
                          └─────────────▲────────────┘
                                        │ PR (End of Day 7 / Tag v0.1.0)
                          ┌─────────────┴────────────┐
                          │   dev (Integration)      │
                          └─────────────▲────────────┘
                                        │ Continuous PRs (Days 1–5) + 1 Peer Approval
           ┌────────────────────────────┼────────────────────────────┐
           │                            │                            │
 ┌─────────┴──────────┐       ┌─────────┴──────────┐       ┌─────────┴──────────┐
 │ feat/engine-akhil  │       │  feat/eval-harry   │       │ feat/proxy-jeremy  │
 └────────────────────┘       └────────────────────┘       └────────────────────┘
```

### 3.1 Golden Rules of Version Control
1. 🛑 **NEVER push code directly to `main` or `dev`.** Pushing straight to `main` or `dev` breaks integration for everyone.
2. 🛠️ **ALL development happens in individual feature branches**:
   - Akhil: `feat/engine-akhil`
   - Harry: `feat/eval-harry`
   - Jeremy: `feat/proxy-jeremy`
3. 🔀 **When to Merge to `dev`? (Merge Cadence)**:
   - **DO NOT wait until Day 6 or Day 7 to merge to `dev`!** That creates "Integration Hell."
   - **Days 1–5 (Continuous Incremental Merging)**: Merge completed sub-tasks to `dev` as soon as they pass unit tests (e.g., Akhil merges `decomposer.py` on Day 2; Harry merges `loader.py` on Day 1).
   - **Day 6 (Code Freeze on `dev`)**: All feature branches MUST be fully merged into `dev` by the end of Day 5 / morning of Day 6. Day 6 is strictly for end-to-end integration testing, bug fixes, and benchmark execution on `dev`.
   - **Day 7 (PR from `dev` -> `main`)**: After the Docker container and Streamlit demo pass on `dev`, Jeremy opens a final Pull Request from `dev` into `main`. All 3 members approve, merge, and tag `v0.1.0-mvp`.

### 3.1.1 Enforced GitHub Branch Protection Rulesets
To programmatically enforce the Golden Rules and protect the repository against accidental destructive operations, active GitHub Rulesets are configured:
* **Ruleset Name:** `Protect Main`
* **Enforcement Status:** `Active`
* **Protected Target Branches:** `main` (Production/Demo) and `dev` (Active Integration)
* **Enforced Governance Policies:**
  - 🔒 **Block Force Pushes:** Enabled — prevents destructive `git push --force` or history rewriting on integration branches.
  - 🛡️ **Restrict Deletions:** Enabled — prevents accidental branch deletion of `main` or `dev`.
  - 👥 **Require Pull Request Before Merging:** Enabled — direct pushes to `main` and `dev` are rejected; all changes must pass through a Pull Request.
  - 📝 **Required Approvals:** Minimum **1 peer review approval** required before PR merge.
  - 🔀 **Allowed Merge Methods:** Merge commit, Squash and merge, Rebase and merge.
  - 👑 **Bypass Rights:** Repository Admin (`Chehrehmi` / Repository Admin Role) has emergency bypass privileges for lead deployment or emergency hotfixes.

### 3.1.2 Day 1 Milestone Integration Record (Status: COMPLETE ✅)
Both Day 1 PRs have been code-reviewed, tested with 100% test coverage, and merged into `dev`:
* ✅ **PR #1 (Harry - Data Pipeline)**: Branch `pr/day1-harry` merged into `dev` (Merge Commit `d8ec0c6`).
  - **Delivered:** `hearsay/dataset/loader.py` (RAGTruth dataset ingestion joining 17,790 records on `source_id`, `load_joined_dataset() -> pd.DataFrame`, `load_as_dataframe()`, and public exports in `hearsay/dataset/__init__.py`).
  - **Test Suite:** `tests/test_loader.py` (8/8 automated tests passed, 100% statement coverage).
* ✅ **PR #2 (Jeremy - Architecture & Proxy)**: Branch `feat/proxy-jeremy` merged into `dev` (Merge Commit `7b4a039`).
  - **Delivered:** `hearsay/proxy/protocol.py` (OpenAI-compatible request/response schemas, Pydantic v2 data models for claims/verdicts, and public exports in `hearsay/proxy/__init__.py`).
  - **Test Suite:** `tests/test_protocol.py` (21/21 automated tests passed, 100% statement coverage).
* 🧪 **Unified Integration Test Suite on `dev`**: **29/29 tests passing** (`pytest tests/ -v`).

---

### 3.2 Member-by-Member Setup & Daily Commands Guide

#### 👤 For AKHIL (ML & Verification Engine)

**Day 1 Initial Setup:**
```bash
# Clone repository
git clone https://github.com/Chehrehmi/hearsay.git
cd hearsay

# Configure git credentials
git config user.name "Akhil"
git config user.email "akhil@example.com"

# Setup virtual environment & dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m spacy download en_core_web_sm

# Create and switch to your feature branch off dev
git checkout dev
git pull origin dev
git checkout -b feat/engine-akhil
git push -u origin feat/engine-akhil
```

**Daily Coding & Push Workflow (Days 1–5):**
```bash
# Always work inside feat/engine-akhil
git status
git add hearsay/engine/

# Write a clean commit message
git commit -m "feat(engine): add spaCy sentence decomposer in decomposer.py"

# Push to your remote feature branch
git push origin feat/engine-akhil

# Open a Pull Request on GitHub: feat/engine-akhil -> dev
# Ask Harry or Jeremy to review and approve!
```

**Syncing your branch with latest `dev` changes:**
```bash
# Keep your branch up to date with dev updates from teammates
git checkout dev
git pull origin dev
git checkout feat/engine-akhil
git merge dev
```

---

#### 👤 For HARRY (Data Pipeline & RAGTruth Evaluation)

**Day 1 Initial Setup:**
```bash
# Clone repository
git clone https://github.com/Chehrehmi/hearsay.git
cd hearsay

# Configure git credentials
git config user.name "Harry"
git config user.email "harry@example.com"

# Setup virtual environment & dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Create and switch to your feature branch off dev
git checkout dev
git pull origin dev
git checkout -b feat/eval-harry
git push -u origin feat/eval-harry
```

**Daily Coding & Push Workflow (Days 1–5):**
```bash
# Always work inside feat/eval-harry
git status
git add hearsay/dataset/ hearsay/eval/

# Write a clean commit message
git commit -m "feat(eval): implement RAGTruth span alignment logic in aligner.py"

# Push to your remote feature branch
git push origin feat/eval-harry

# Open a Pull Request on GitHub: feat/eval-harry -> dev
# Ask Akhil or Jeremy to review and approve!
```

---

#### 👤 For JEREMY (Proxy Gateway, Trace DB & Dashboard)

**Day 1 Initial Setup:**
```bash
# Repo is already cloned in /Users/jeremy/CUSAT/Hearsay-Project/hearsay
cd /Users/jeremy/CUSAT/Hearsay-Project/hearsay

# Configure git credentials
git config user.name "Chehrehmi"
git config user.email "jeremymathewjose@gmail.com"

# Create and switch to your feature branch off dev
git checkout dev
git pull origin dev
git checkout -b feat/proxy-jeremy
git push -u origin feat/proxy-jeremy
```

**Daily Coding & Push Workflow (Days 1–5):**
```bash
# Always work inside feat/proxy-jeremy
git status
git add hearsay/proxy/ hearsay/db/ hearsay/ui/

# Write a clean commit message
git commit -m "feat(proxy): implement FastAPI /verify endpoint in gateway.py"

# Push to your remote feature branch
git push origin feat/proxy-jeremy

# Open a Pull Request on GitHub: feat/proxy-jeremy -> dev
# Ask Akhil or Harry to review and approve!
```

---

## 4. Team Member Division of Labor & Daily Schedule

Each team member works **5 hours per day for 7 days (Total: 35 hours / person)**.

---

### Member 1: AKHIL — ML, NLI Engine & Claim Decomposition
**Primary Role:** ML Systems Engineer  
**Core Responsibilities:** Claim decomposition, Bi-Encoder retrieval, Cross-Encoder NLI classification, verification pipeline optimization.

#### What to Do:
- Build `hearsay/engine/decomposer.py` to break LLM response text into clean, atomic sentence/clause claims.
- Build `hearsay/engine/retriever.py` to index source chunks and retrieve top-k candidate evidence spans using `sentence-transformers` (`all-MiniLM-L6-v2`).
- Build `hearsay/engine/verifier.py` to evaluate Premise-Hypothesis pairs using `cross-encoder/nli-deberta-v3-small` (PyTorch / ONNX INT8).
- Build `hearsay/engine/pipeline.py` to expose a clean `HearsayEngine.verify(response, source_info)` API.

#### Daily Schedule & Hour Allocations (35 Hours Total):

| Day | Hours | Tasks & Deliverables | Merge Target |
|---|---|---|---|
| **Day 1** | 5h | Setup ML virtual environment, install `transformers`, `torch`, `spacy`. Prototype spaCy sentence segmentation. | Branch `feat/engine-akhil` |
| **Day 2** | 5h | Develop `decomposer.py`. Add conjunction splitting (`and`, `but`, `;`). PR to `dev`. | **PR -> `dev`** |
| **Day 3** | 5h | Develop `retriever.py`. Implement chunk chunking & `all-MiniLM-L6-v2` bi-encoder scoring. PR to `dev`. | **PR -> `dev`** |
| **Day 4** | 5h | Develop `verifier.py`. Load `nli-deberta-v3-small`. Formulate (Premise, Hypothesis) pairs. PR to `dev`. | **PR -> `dev`** |
| **Day 5** | 5h | Assemble `pipeline.py`. Combine Decomposer → Retriever → Verifier. PR to `dev`. | **PR -> `dev` (Code Freeze)** |
| **Day 6** | 5h | Integration Testing & Calibration on `dev`. Tune confidence threshold ($\tau = 0.65$). Handle edge cases. | On `dev` branch |
| **Day 7** | 5h | Unit tests (`test_engine.py`), documentation, assist in final PR `dev` -> `main`. | **Merge `dev` -> `main`** |

---

### Member 2: HARRY — Data Pipeline, RAGTruth Alignment & Benchmark Metrics
**Primary Role:** Data & Benchmark Evaluation Lead  
**Core Responsibilities:** RAGTruth dataset processing, label alignment, quantitative metrics evaluation, benchmark runner CLI, latency/cost profiling.

#### What to Do:
- Build `hearsay/dataset/loader.py` to parse and validate `source_info.jsonl` and `response.jsonl`.
- Build `hearsay/eval/aligner.py` to map RAGTruth word/phrase-level ground truth labels (`Evident Conflict`, `Subtle Conflict`, `Evident Baseless Info`, `Subtle Baseless Info`) to sentence/claim-level binary predictions (`Supported` vs. `Unsupported`).
- Build `hearsay/eval/metrics.py` to compute Precision, Recall, F1, Accuracy, and per-task breakdowns (QA MS MARCO, Summarization CNN/DM, Data-to-Text Yelp).
- Build `hearsay/eval/benchmark_runner.py` CLI script to run evaluations over sample/full datasets and produce `benchmark_results.json` and Markdown summary tables.

#### Daily Schedule & Hour Allocations (35 Hours Total):

| Day | Hours | Tasks & Deliverables | Merge Target |
|---|---|---|---|
| **Day 1** | 5h | Inspect dataset files `source_info.jsonl` and `response.jsonl`. Write `loader.py`. PR to `dev`. | **PR -> `dev`** |
| **Day 2** | 5h | Develop `aligner.py`. Build span-overlap logic: map RAGTruth character offsets to sentence boundaries. PR to `dev`. | **PR -> `dev`** |
| **Day 3** | 5h | Develop `metrics.py`. Implement sentence-level Precision, Recall, F1 computation. PR to `dev`. | **PR -> `dev`** |
| **Day 4** | 5h | Develop `benchmark_runner.py`. Wire up Akhil's `HearsayEngine` to evaluate 100 RAGTruth samples. PR to `dev`. | **PR -> `dev`** |
| **Day 5** | 5h | Execute full benchmark run (1,000+ instances). Compute per-task metrics (QA vs. Summary vs. Yelp). Record P50/P95 latency. | **PR -> `dev` (Code Freeze)** |
| **Day 6** | 5h | Error Analysis & Failure Mode Taxonomy. Identify top 10 false positives/negatives. Generate summary tables. | On `dev` branch |
| **Day 7** | 5h | Final evaluation write-up, benchmark charts generation, code cleanup (`test_eval.py`), assist in final `dev` -> `main` PR. | **Merge `dev` -> `main`** |

---

### Member 3: JEREMY — Proxy Gateway, API Contracts, Trace DB & Evidence Dashboard
**Primary Role:** Systems Architecture & Full-Stack Lead  
**Core Responsibilities:** FastAPI reverse proxy gateway, OpenAI context protocol parser, SQLite audit trace store, Streamlit evidence observability UI, Docker packaging.

#### What to Do:
- Build `hearsay/proxy/protocol.py` defining Pydantic request/response schemas for `/v1/chat/completions` and `/verify`.
- Build `hearsay/proxy/gateway.py` implementing FastAPI proxy middleware that intercepts requests, extracts context, invokes `HearsayEngine`, and returns sanitized/annotated JSON outputs.
- Build `hearsay/db/trace_store.py` implementing SQLite database storage (`hearsay_traces.db`) for requests, claims, NLI verdicts, confidence scores, and latency traces.
- Build `hearsay/ui/dashboard.py` (Streamlit app) showing side-by-side claim-to-evidence span highlighting (green for Supported, red for Contradicted, yellow for Ungrounded), confidence score pills, and retrieval telemetry.
- Package the system with `Dockerfile` and `docker-compose.yml`.

#### Daily Schedule & Hour Allocations (35 Hours Total):

| Day | Hours | Tasks & Deliverables | Merge Target |
|---|---|---|---|
| **Day 1** | 5h | Package skeleton setup (`hearsay/`). Build `protocol.py` Pydantic models. PR to `dev`. | **PR -> `dev`** |
| **Day 2** | 5h | Build `gateway.py` skeleton. Implement `/v1/chat/completions` route & header parser. PR to `dev`. | **PR -> `dev`** |
| **Day 3** | 5h | Build `trace_store.py`. Implement SQLite DB schema (`requests`, `claims`, `verdicts`). PR to `dev`. | **PR -> `dev`** |
| **Day 4** | 5h | Integrate Gateway with Akhil's `HearsayEngine`. Store trace in SQLite DB on every API call. PR to `dev`. | **PR -> `dev`** |
| **Day 5** | 5h | Build `dashboard.py` Streamlit UI. Implement interactive trace selector & evidence highlighting. PR to `dev`. | **PR -> `dev` (Code Freeze)** |
| **Day 6** | 5h | Telemetry & retrieval diagnostics panel (P50/P95 latency graphs, unused chunk warnings). End-to-end testing on `dev`. | On `dev` branch |
| **Day 7** | 5h | Create `Dockerfile` & `docker-compose.yml`. Final PR `dev` -> `main`, record 2-minute video demo. | **Merge `dev` -> `main`** |

---

## 5. API Contracts & Data Specifications

To allow all 3 team members to work concurrently without blocking each other, the data contracts between modules are frozen as follows:

### 5.1 Request Protocol Contract (`hearsay/proxy/protocol.py`)
```python
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class ContextPayload(BaseModel):
    source_id: str
    source_info: str # Full retrieved context string or concatenated chunks

class VerificationRequest(BaseModel):
    model: str = "gpt-3.5-turbo"
    messages: List[Dict[str, str]]
    response_text: Optional[str] = None # If verifying pre-generated text
    verirag_context: Optional[ContextPayload] = None
```

### 5.2 Engine Verification Verdict Contract (`hearsay/engine/pipeline.py`)
```python
class ClaimVerdict(BaseModel):
    claim_id: int
    claim_text: str
    status: str # "Supported" | "Unsupported (Contradiction)" | "Unsupported (Ungrounded)"
    confidence: float # 0.0 to 1.0
    evidence_span: Optional[str] = None
    source_chunk_id: Optional[str] = None
    nli_logits: Dict[str, float] # {"entailment": 0.92, "neutral": 0.05, "contradiction": 0.03}

class VerificationResult(BaseModel):
    request_id: str
    overall_status: str # "Verified" | "Hallucination Detected"
    groundedness_score: float # Percentage of supported claims (0.0 to 100.0)
    total_claims: int
    supported_claims: int
    contradicted_claims: int
    ungrounded_claims: int
    claims: List[ClaimVerdict]
    latency_ms: float
```

---

## 6. Complete Starter Templates for Each Team Member

Below are complete, copy-pasteable starter templates for every single file in the project.

### 6.1 Akhil's Implementation Files (`hearsay/engine/`)

#### 📄 `hearsay/engine/decomposer.py`
```python
import spacy
import re

class ClaimDecomposer:
    def __init__(self):
        self.nlp = spacy.load("en_core_web_sm")

    def decompose(self, text: str) -> list[str]:
        """Decomposes response prose into discrete atomic sentence/clause claims."""
        doc = self.nlp(text)
        sentences = [sent.text.strip() for sent in doc.sents if len(sent.text.strip()) > 5]
        claims = []
        for sent in sentences:
            # Sub-split long clauses on conjunctions if explicit clauses exist
            sub_clauses = re.split(r';|\b(?:and|but|whereas)\b', sent)
            for clause in sub_clauses:
                cleaned = clause.strip()
                if len(cleaned.split()) >= 3:
                    claims.append(cleaned)
        return claims if claims else [text]
```

#### 📄 `hearsay/engine/retriever.py`
```python
from sentence_transformers import SentenceTransformer, util
import spacy

class BiEncoderRetriever:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)
        self.nlp = spacy.load("en_core_web_sm")

    def get_candidate_spans(self, source_info: str, claim: str, top_k: int = 3) -> list[dict]:
        """Chunks source_info by sentence and ranks top-k candidate evidence spans by bi-encoder similarity."""
        doc = self.nlp(source_info)
        source_sentences = [sent.text.strip() for sent in doc.sents if len(sent.text.strip()) > 10]
        if not source_sentences:
            return [{"chunk": source_info, "score": 1.0}]
            
        claim_embedding = self.model.encode(claim, convert_to_tensor=True)
        chunk_embeddings = self.model.encode(source_sentences, convert_to_tensor=True)
        
        scores = util.cos_sim(claim_embedding, chunk_embeddings)[0]
        top_results = scores.topk(k=min(top_k, len(source_sentences)))
        
        candidates = []
        for score, idx in zip(top_results.values, top_results.indices):
            candidates.append({
                "chunk": source_sentences[idx.item()],
                "score": round(float(score.item()), 4)
            })
        return candidates
```

#### 📄 `hearsay/engine/verifier.py`
```python
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch

class NLIClassifier:
    def __init__(self, model_name: str = "cross-encoder/nli-deberta-v3-small"):
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_name)
        self.model.eval()

    def predict(self, premise: str, hypothesis: str) -> dict:
        """Classifies Premise (Source Chunk) and Hypothesis (Claim) into Supported, Contradiction, or Ungrounded."""
        inputs = self.tokenizer(premise, hypothesis, return_tensors="pt", truncation=True, max_length=512)
        with torch.no_grad():
            logits = self.model(**inputs).logits.squeeze(0)
            probs = torch.softmax(logits, dim=-1).tolist()
        
        id2label = self.model.config.id2label
        probs_dict = {id2label[i].lower(): probs[i] for i in range(len(probs))}
        
        entailment = probs_dict.get("entailment", 0.0)
        contradiction = probs_dict.get("contradiction", 0.0)
        neutral = probs_dict.get("neutral", 0.0)
        
        if entailment >= 0.60:
            status = "Supported"
            confidence = entailment
        elif contradiction >= 0.50:
            status = "Unsupported (Contradiction)"
            confidence = contradiction
        else:
            status = "Unsupported (Ungrounded)"
            confidence = max(neutral, 1.0 - entailment)
            
        return {
            "status": status,
            "confidence": round(confidence, 4),
            "logits": probs_dict
        }
```

#### 📄 `hearsay/engine/pipeline.py`
```python
import time
import uuid
from hearsay.engine.decomposer import ClaimDecomposer
from hearsay.engine.retriever import BiEncoderRetriever
from hearsay.engine.verifier import NLIClassifier

class HearsayEngine:
    def __init__(self):
        self.decomposer = ClaimDecomposer()
        self.retriever = BiEncoderRetriever()
        self.verifier = NLIClassifier()

    def verify(self, response_text: str, source_info: str) -> dict:
        """Main end-to-end verification pipeline entrypoint."""
        start_time = time.perf_counter()
        claims = self.decomposer.decompose(response_text)
        
        verdicts = []
        supported_count = 0
        contradicted_count = 0
        ungrounded_count = 0
        
        for idx, claim in enumerate(claims):
            candidates = self.retriever.get_candidate_spans(source_info, claim, top_k=1)
            best_evidence = candidates[0]["chunk"] if candidates else source_info
            
            nli_result = self.verifier.predict(premise=best_evidence, hypothesis=claim)
            status = nli_result["status"]
            
            if status == "Supported":
                supported_count += 1
            elif "Contradiction" in status:
                contradicted_count += 1
            else:
                ungrounded_count += 1
                
            verdicts.append({
                "claim_id": idx,
                "claim_text": claim,
                "status": status,
                "confidence": nli_result["confidence"],
                "evidence_span": best_evidence,
                "nli_logits": nli_result["logits"]
            })
            
        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
        total = len(claims)
        groundedness_score = round((supported_count / total * 100.0) if total > 0 else 0.0, 2)
        
        return {
            "request_id": str(uuid.uuid4())[:8],
            "overall_status": "Verified" if ungrounded_count == 0 and contradicted_count == 0 else "Hallucination Detected",
            "groundedness_score": groundedness_score,
            "total_claims": total,
            "supported_claims": supported_count,
            "contradicted_claims": contradicted_count,
            "ungrounded_claims": ungrounded_count,
            "claims": verdicts,
            "latency_ms": elapsed_ms
        }
```

---

### 6.2 Harry's Implementation Files (`hearsay/dataset/` & `hearsay/eval/`)

#### 📄 `hearsay/dataset/loader.py`
```python
import json
from pathlib import Path
from typing import List, Dict, Any, Union
import pandas as pd

class RAGTruthLoader:
    """Loader and preprocessor for the RAGTruth benchmark dataset."""

    def __init__(self, data_dir: Union[str, Path] = "data"):
        self.data_dir = Path(data_dir)

    def load_sources(self) -> List[Dict[str, Any]]:
        source_file = self.data_dir / "source_info.jsonl"
        sources = []
        with open(source_file, "r", encoding="utf-8") as file:
            for line in file:
                if line.strip():
                    sources.append(json.loads(line))
        return sources

    def load_responses(self) -> List[Dict[str, Any]]:
        response_file = self.data_dir / "response.jsonl"
        responses = []
        with open(response_file, "r", encoding="utf-8") as file:
            for line in file:
                if line.strip():
                    responses.append(json.loads(line))
        return responses

    def load(self) -> List[Dict[str, Any]]:
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
        """Loads and joins sources and responses into a pandas DataFrame."""
        return pd.DataFrame(self.load())

    def load_as_dataframe(self) -> pd.DataFrame:
        """Convenience alias for load_joined_dataset()."""
        return self.load_joined_dataset()
```


#### 📄 `hearsay/eval/aligner.py`
```python
class RAGTruthAligner:
    @staticmethod
    def align_sentence_labels(response_text: str, labels: list[dict], sentences: list[str]) -> list[dict]:
        """Maps RAGTruth character offset labels (start, end) to discrete sentence predictions."""
        sentence_targets = []
        current_offset = 0
        
        for sent in sentences:
            sent_start = response_text.find(sent, current_offset)
            if sent_start == -1:
                sent_start = current_offset
            sent_end = sent_start + len(sent)
            current_offset = sent_end
            
            has_hallucination = False
            label_type = "Supported"
            for lbl in labels:
                l_start, l_end = lbl["start"], lbl["end"]
                if max(sent_start, l_start) < min(sent_end, l_end):
                    has_hallucination = True
                    label_type = lbl.get("label_type", "Hallucination")
                    break
                    
            sentence_targets.append({
                "sentence": sent,
                "is_hallucination": 1 if has_hallucination else 0,
                "label_type": label_type
            })
            
        return sentence_targets
```

#### 📄 `hearsay/eval/metrics.py`
```python
from sklearn.metrics import precision_score, recall_score, f1_score, accuracy_score

def compute_groundedness_metrics(y_true: list[int], y_pred: list[int]) -> dict:
    """y_true: 1 for Unsupported/Hallucinated, 0 for Supported."""
    return {
        "precision": round(float(precision_score(y_true, y_pred, zero_division=0)), 4),
        "recall": round(float(recall_score(y_true, y_pred, zero_division=0)), 4),
        "f1": round(float(f1_score(y_true, y_pred, zero_division=0)), 4),
        "accuracy": round(float(accuracy_score(y_true, y_pred)), 4)
    }
```

#### 📄 `hearsay/eval/benchmark_runner.py`
```python
import json
import argparse
from hearsay.dataset.loader import RAGTruthLoader
from hearsay.eval.aligner import RAGTruthAligner
from hearsay.eval.metrics import compute_groundedness_metrics
from hearsay.engine.pipeline import HearsayEngine

def run_benchmark(sample_limit: int = 100):
    print(f"🚀 Running Hearsay RAGTruth Benchmark on {sample_limit} instances...")
    loader = RAGTruthLoader()
    df = loader.load_joined_dataset().head(sample_limit)
    engine = HearsayEngine()
    
    y_true = []
    y_pred = []
    latencies = []
    
    for idx, row in df.iterrows():
        response_text = row["response"]
        source_info = row["source_info"]
        labels = row["labels"]
        
        result = engine.verify(response_text, source_info)
        latencies.append(result["latency_ms"])
        
        sentences = [c["claim_text"] for c in result["claims"]]
        aligned = RAGTruthAligner.align_sentence_labels(response_text, labels, sentences)
        
        for item, verdict in zip(aligned, result["claims"]):
            y_true.append(item["is_hallucination"])
            pred_val = 0 if verdict["status"] == "Supported" else 1
            y_pred.append(pred_val)
            
    metrics = compute_groundedness_metrics(y_true, y_pred)
    avg_latency = round(sum(latencies) / len(latencies), 2) if latencies else 0
    
    summary = {
        "samples_evaluated": len(df),
        "total_sentences": len(y_true),
        "metrics": metrics,
        "avg_latency_ms": avg_latency
    }
    
    print("\n================ BENCHMARK RESULTS ================")
    print(json.dumps(summary, indent=2))
    print("===================================================\n")
    
    with open("benchmark_results.json", "w") as f:
        json.dump(summary, f, indent=2)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=50, help="Number of RAGTruth samples to evaluate")
    args = parser.parse_args()
    run_benchmark(sample_limit=args.limit)
```

---

### 6.3 Jeremy's Implementation Files (`hearsay/proxy/`, `hearsay/db/`, `hearsay/ui/`)

#### 📄 `hearsay/proxy/protocol.py`
```python
from pydantic import BaseModel
from typing import List, Optional, Dict

class ContextPayload(BaseModel):
    source_id: str
    source_info: str

class VerificationRequest(BaseModel):
    model: str = "gpt-3.5-turbo"
    messages: List[Dict[str, str]]
    response_text: Optional[str] = None
    verirag_context: Optional[ContextPayload] = None
```

#### 📄 `hearsay/proxy/gateway.py`
```python
from fastapi import FastAPI, HTTPException
from hearsay.proxy.protocol import VerificationRequest
from hearsay.engine.pipeline import HearsayEngine
from hearsay.db.trace_store import TraceStore

app = FastAPI(title="Hearsay Gateway API", version="0.1.0-mvp")
engine = HearsayEngine()
db = TraceStore()

@app.post("/verify")
async def verify_response(req: VerificationRequest):
    if not req.response_text or not req.verirag_context:
        raise HTTPException(status_code=400, detail="response_text and verirag_context are required.")
        
    result = engine.verify(req.response_text, req.verirag_context.source_info)
    db.log_trace(result, req.response_text, req.verirag_context.source_id)
    return result

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "hearsay-gateway"}
```

#### 📄 `hearsay/db/trace_store.py`
```python
import sqlite3
import json
from datetime import datetime

class TraceStore:
    def __init__(self, db_path: str = "hearsay_traces.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS traces (
                    request_id TEXT PRIMARY KEY,
                    timestamp TEXT,
                    source_id TEXT,
                    response_text TEXT,
                    overall_status TEXT,
                    groundedness_score REAL,
                    total_claims INTEGER,
                    latency_ms REAL,
                    result_json TEXT
                )
            """)

    def log_trace(self, result: dict, response_text: str, source_id: str):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO traces VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                result["request_id"],
                datetime.utcnow().isoformat(),
                source_id,
                response_text,
                result["overall_status"],
                result["groundedness_score"],
                result["total_claims"],
                result["latency_ms"],
                json.dumps(result)
            ))
```

#### 📄 `hearsay/ui/dashboard.py`
```python
import streamlit as st
import sqlite3
import json

st.set_page_config(page_title="Hearsay Observability Dashboard", layout="wide")
st.title("🛡️ Hearsay: RAG Groundedness Observability Gateway")

conn = sqlite3.connect("hearsay_traces.db")
traces = conn.execute("SELECT request_id, timestamp, overall_status, groundedness_score, latency_ms FROM traces ORDER BY timestamp DESC").fetchall()

if not traces:
    st.info("No verification traces recorded yet. Send requests to the Hearsay Proxy Gateway!")
else:
    selected_id = st.sidebar.selectbox("Select Request Trace", [t[0] for t in traces])
    row = conn.execute("SELECT result_json FROM traces WHERE request_id = ?", (selected_id,)).fetchone()
    data = json.loads(row[0])

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Status", data["overall_status"])
    col2.metric("Groundedness Score", f"{data['groundedness_score']}%")
    col3.metric("Total Claims", data["total_claims"])
    col4.metric("Latency", f"{data['latency_ms']} ms")

    st.subheader("Claim-Level Evidence Map")
    for claim in data["claims"]:
        status = claim["status"]
        color = "#d4edda" if status == "Supported" else ("#f8d7da" if "Contradiction" in status else "#fff3cd")
        
        with st.container():
            st.markdown(
                f"""
                <div style="background-color: {color}; padding: 12px; border-radius: 8px; margin-bottom: 8px; color: #111;">
                    <strong>Claim:</strong> {claim['claim_text']}<br>
                    <strong>Status:</strong> {status} (Confidence: {claim['confidence']})<br>
                    <small><strong>Evidence:</strong> {claim.get('evidence_span', 'N/A')}</small>
                </div>
                """,
                unsafe_html=True
            )
```

---

## 7. Week 1 MVP Acceptance & Demo Checklist

Before presenting to the guide on Day 7, verify all items:

- [ ] `hearsay` package imports cleanly with zero errors (`python -c "import hearsay"`).
- [ ] Akhil's NLI engine verifies an input sentence against context in under 150ms on standard CPU.
- [ ] Harry's evaluation script runs on `response.jsonl` and outputs clean Precision, Recall, and F1 metrics tables.
- [ ] Jeremy's FastAPI proxy gateway responds to HTTP POST `/verify` and logs traces to `hearsay_traces.db`.
- [ ] Streamlit dashboard launches via `streamlit run hearsay/ui/dashboard.py` and visually renders highlighted green/red/yellow claims.
- [ ] Docker container builds cleanly with `docker compose up` and exposes the gateway on port `8000`.
- [ ] Final PR opened from `dev` to `main`, peer reviewed by all 3 members, merged, and tagged `v0.1.0-mvp`.
- [ ] 2-minute video walkthrough recorded demonstrating live verification of a hallucinated RAG sentence.

---

## 8. Summary of Responsibilities & Branch Targets

| Team Member | Module Ownership | Deliverables | Feature Branch | Merge Target |
|---|---|---|---|---|
| **Akhil** | Engine & ML | `decomposer.py`, `retriever.py`, `verifier.py`, `pipeline.py` | `feat/engine-akhil` | Daily PRs -> `dev` (Code freeze Day 5) |
| **Harry** | Data & Evaluation | `loader.py`, `aligner.py`, `metrics.py`, `benchmark_runner.py` | `feat/eval-harry` | Daily PRs -> `dev` (Code freeze Day 5) |
| **Jeremy** | Proxy & UI | `protocol.py`, `gateway.py`, `trace_store.py`, `dashboard.py`, `docker-compose.yml` | `feat/proxy-jeremy` | Daily PRs -> `dev` (Code freeze Day 5) |
