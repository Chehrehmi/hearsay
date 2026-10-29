# RAG Chatbot Companion (Dual-Mode) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a split-screen interactive RAG Chatbot Companion tab in the Hearsay React SPA (Port 5173) backed by the FastAPI Gateway (Port 8000) that demonstrates real-time groundedness verification, claim decomposition, evidence inspection, and dual-mode execution (Offline Benchmark Corpus + Optional Live Gemini LLM Proxy).

**Architecture:** A responsive split-view interface where the left panel renders an interactive RAG chat conversation and the right panel renders the Hearsay Verification & Evidence Inspector. Queries hit `POST /verify` or `POST /v1/chat/completions` on the local FastAPI proxy, logging traces directly to SQLite `hearsay_traces.db` and returning live NLI entailment scores, claim breakdowns, and source evidence spans.

**Tech Stack:** React 18, TypeScript, Tailwind CSS, Vite, Lucide React icons, FastAPI, PyTorch (DeBERTa-v3-small), SQLite (TraceStore).

**Spec:** `docs/specs/2026-10-29-rag-companion-design.md`

## Global Constraints

- **Anti-Slop Strictness:** Every percentage, status, and claim displayed must come directly from `/verify` API response or benchmark datasets; no synthetic mock percentages or fake SLA numbers.
- **Offline Reliability:** Default mode must work 100% offline without any API keys or network connection (safe for CUSAT viva).
- **Design Tokens:** Background `#FAF8F3`, primary surface `#FFFFFF`, border `#D9D4C7`, text `#0C0C12`, active button scale `0.96`, transitions gated with `motion-safe:`.
- **FastAPI Port:** Gateway operates on `http://localhost:8000`, frontend on `http://localhost:5173`.
- **Zero Breaking Changes:** Existing tabs (`sandbox`, `adversarial`, `traces`, `analytics`) and all 118 existing unit tests must remain 100% passing.

## Review Focus

1. **Empty Query / Missing Context:** Submitting an empty prompt or query with no documents must gracefully display a warning banner without crashing the UI or throwing a 500.
2. **Network Offline / Gateway Down:** If port 8000 is not running, the companion must show an inline amber warning card with retry guidance rather than an unhandled promise rejection.
3. **Severe Contradiction Handling:** When an LLM asserts a direct historical contradiction (e.g. "Anne Frank died in 2022"), the badge must clearly render red (Contradicted) and highlight the exact conflicting source chunk in the drawer.
4. **Epistemic Hedging Evasion:** When a user toggles adversarial hedging injection ("According to reports..."), the inspector must show both the raw claim, the sanitized claim, and the final gate verdict.
5. **Trace Navigation Continuity:** Clicking "Inspect in Trace Explorer" on any verified message must transition `activeTab` to `'traces'` with that trace's `request_id` or query automatically focused.

---

### Task 1: Curated Knowledge Corpus & Companion Backend Helper

**Files:**
- Create: `hearsay/hearsay/demo/corpus.py`
- Modify: `hearsay/hearsay/proxy/gateway.py:45-80`
- Test: `hearsay/tests/test_demo_corpus.py`

**Interfaces:**
- Consumes: `hearsay.dataset.alce_loader.ALCELoader`, `hearsay.dataset.loader.RAGTruthLoader`
- Produces: `get_curated_rag_samples() -> List[Dict[str, Any]]`, `GET /v1/demo/corpus` endpoint

- [ ] **Step 1: Write the failing test for demo corpus provider**

```python
# hearsay/tests/test_demo_corpus.py
import pytest
from hearsay.demo.corpus import get_curated_rag_samples

def test_get_curated_rag_samples_returns_valid_entries():
    samples = get_curated_rag_samples()
    assert len(samples) >= 3
    for s in samples:
        assert "id" in s
        assert "title" in s
        assert "category" in s # "Faithful RAG", "Hallucinated RAG", "Adversarial Evasion"
        assert "question" in s
        assert "context" in s
        assert "expected_response" in s
        assert len(s["context"]) > 20
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd hearsay && ./.venv/bin/pytest tests/test_demo_corpus.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'hearsay.demo'`

- [ ] **Step 3: Implement `corpus.py` and register `GET /v1/demo/corpus` in `gateway.py`**

Create `hearsay/hearsay/demo/corpus.py` exposing 4 curated, authentic benchmark scenarios:
1. *Anne Frank Historical Belsen Archives* (RAGTruth faithful vs contradiction)
2. *World Football Goal Scoring Records* (ALCE ASQA with citation brackets `[1]`, `[2]`)
3. *Wan Chai Hong Kong Police Case* (RAGTruth summary)
4. *Epistemic Hedging Evasion Test* (Demonstrating defense)

Register `GET /v1/demo/corpus` in `hearsay/hearsay/proxy/gateway.py` returning this list.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd hearsay && ./.venv/bin/pytest tests/test_demo_corpus.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd hearsay
git add hearsay/demo/ tests/test_demo_corpus.py hearsay/proxy/gateway.py
git commit -m "feat(demo): add curated RAG knowledge corpus and API endpoint"
```

---

### Task 2: Optional Gemini / Upstream Live LLM Proxy Handler in Gateway

**Files:**
- Modify: `hearsay/hearsay/proxy/gateway.py:76-140`
- Test: `hearsay/tests/test_live_proxy.py`

**Interfaces:**
- Consumes: Optional `GEMINI_API_KEY` or `OPENAI_API_KEY` environment variables, or request headers
- Produces: Live upstream completion forwarding with inline Hearsay verification and SQLite audit logging

- [ ] **Step 1: Write test for chat completion proxy with injected context**

```python
# hearsay/tests/test_live_proxy.py
from fastapi.testclient import TestClient
from hearsay.proxy.gateway import app

client = TestClient(app)

def test_chat_completions_with_context_verifies_and_logs():
    payload = {
        "model": "hearsay-verified",
        "messages": [
            {"role": "user", "content": "When did Anne Frank die?"}
        ],
        "response_text": "Anne Frank died in March 1945 in Bergen-Belsen.",
        "verirag_context": {
            "source_id": "doc-anne-frank",
            "text": "Seventy years ago, Anne Frank died of typhus in a Nazi concentration camp at the age of 15 in March 1945."
        }
    }
    res = client.post("/v1/chat/completions", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "hearsay_verification" in data
    assert data["hearsay_verification"]["overall_status"] == "Supported"
```

- [ ] **Step 2: Run test to verify it passes or fails**

Run: `cd hearsay && ./.venv/bin/pytest tests/test_live_proxy.py -v`
Expected: PASS (validates existing endpoint contract).

- [ ] **Step 3: Add support for optional Gemini live generation fallback if API key is provided**

In `hearsay/hearsay/proxy/gateway.py`, if `req.messages` is present and `req.response_text` is empty:
- If `GEMINI_API_KEY` or `X-Gemini-Key` header is set, call Google Gemini 2.5 Flash / 1.5 Flash endpoint via `urllib.request` or `httpcore`, passing context in system prompt.
- If no API key is set, use context-aware extractive answer fallback so it works 100% offline.
- Route generated answer through `_execute_verification(text, context)`.
- Commit trace to `TraceStore`.

- [ ] **Step 4: Run unit tests to verify no regressions**

Run: `cd hearsay && ./.venv/bin/pytest tests/test_gateway.py tests/test_live_proxy.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd hearsay
git add hearsay/proxy/gateway.py tests/test_live_proxy.py
git commit -m "feat(gateway): enable upstream Gemini proxy routing with inline verification"
```

---

### Task 3: Build the Frontend `RAGCompanionView.tsx` Component

**Files:**
- Create: `hearsay/frontend/src/components/RAGCompanionView.tsx`
- Modify: `hearsay/frontend/src/types.ts:1-40`
- Test: Component compilation via `npm run build`

**Interfaces:**
- Consumes: `GET /v1/demo/corpus`, `POST /verify`, `POST /v1/chat/completions`
- Produces: Responsive split-screen interactive RAG UI with evidence drawer and deep-linking callback `onNavigateToTrace(requestId: string)`

- [ ] **Step 1: Define TypeScript interfaces in `types.ts`**

Add `RAGMessage`, `CuratedCorpusItem`, and `CompanionMode` types to `hearsay/frontend/src/types.ts`.

- [ ] **Step 2: Implement `RAGCompanionView.tsx`**

Implement split-screen layout adhering to `/better-ui`:
1. **Header Toolbar**:
   - Scenario Selector dropdown (Curated ASQA, RAGTruth, Epistemic Hedging, Custom).
   - Mode Toggle pill: "Curated Benchmark (Offline Safe)" vs "Live Gemini Gateway".
   - Clear Conversation button.
2. **Left Panel: Conversational Timeline (60%)**:
   - Chat bubbles with user queries and assistant responses.
   - Status badge under each assistant bubble:
     - 🟢 **Grounded (100%)**
     - 🔴 **Contradiction Detected**
     - 🟡 **Ungrounded Claims Found**
   - Interactive button: "Inspect Verification & Evidence".
   - Bottom input bar with Send button (active:scale-96), prompt suggestions.
3. **Right Panel: Hearsay Evidence & Telemetry Inspector (40%)**:
   - Active Request ID badge.
   - Retrieved Context accordion (shows the exact Wikipedia / document chunk passed to the LLM).
   - Claim Breakdown list:
     - Each individual sentence claim with NLI entailment / contradiction probabilities.
     - Extracted evidence span highlighting.
   - Action link: "Inspect in Trace Explorer →" (invokes `onNavigateToTrace`).

- [ ] **Step 3: Run TypeScript typecheck and Vite build**

Run: `cd hearsay/frontend && npm run build`
Expected: 0 errors, build succeeds in <300ms.

- [ ] **Step 4: Commit**

```bash
cd hearsay
git add frontend/src/components/RAGCompanionView.tsx frontend/src/types.ts
git commit -m "feat(ui): add interactive split-screen RAG Companion view"
```

---

### Task 4: Mount Companion Tab in Main Navigation (`App.tsx`)

**Files:**
- Modify: `hearsay/frontend/src/App.tsx:9-30, 105-140, 310-330`
- Test: Vite build & browser verification

**Interfaces:**
- Consumes: `RAGCompanionView`
- Produces: Navigation tab `'companion'` under Main, deep-link routing from companion to `'traces'`

- [ ] **Step 1: Update `activeTab` state and navigation in `App.tsx`**

1. Expand `activeTab` union type: `'sandbox' | 'adversarial' | 'traces' | 'analytics' | 'companion'`.
2. Add "RAG Chatbot Companion" button under "Main" navigation section with a chat bubble icon.
3. Wire tab render:
```tsx
{activeTab === 'companion' && (
  <RAGCompanionView
    apiBase={apiBase}
    onNavigateToTrace={(reqId) => {
      setGlobalSearch(reqId);
      setActiveTab('traces');
    }}
  />
)}
```

- [ ] **Step 2: Run Vite production build**

Run: `cd hearsay/frontend && npm run build`
Expected: Build succeeds cleanly.

- [ ] **Step 3: Commit**

```bash
cd hearsay
git add frontend/src/App.tsx
git commit -m "feat(ui): integrate RAG Companion tab into main navigation"
```

---

### Task 5: End-to-End Test Suite & Verification

**Files:**
- Modify: `hearsay/tests/test_gateway.py`
- Run: Full pytest suite + frontend build check

- [ ] **Step 1: Run complete backend pytest suite**

Run: `cd hearsay && ./.venv/bin/pytest tests/ -v`
Expected: All tests pass (118+ tests).

- [ ] **Step 2: Build frontend distribution files for FastAPI static mount**

Run: `cd hearsay/frontend && npm run build`
Expected: Static assets written to `hearsay/frontend/dist/`.

- [ ] **Step 3: Final Git Checkpoint**

```bash
cd hearsay
git status
git commit -m "chore(release): complete RAG Chatbot Companion with dual-mode verification"
```
