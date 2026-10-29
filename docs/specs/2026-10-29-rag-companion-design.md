# Design Document: Hearsay Live RAG Chatbot Companion (Dual-Mode)

**Date:** 2026-10-29  
**Status:** Pending Approval  
**Author:** Jeremy (MCA Mini-Project, CUSAT)  
**Evaluators:** Dr. M. V. Judy (Guide), Devdutt (PhD Scholar), Dr. Vinod P. (HOD)  
**Target:** 3rd Semester MCA Mini-Project (Course 22-382-0303)  

---

## 1. Intent & The Why

Hearsay was designed as a lightweight, privacy-preserving verification gateway for enterprise RAG pipelines. However, in an academic defense and product demonstration, showing only offline tables or static audit logs does not convey how Hearsay actively protects end-users. 

The **RAG Chatbot Companion** provides a split-screen, interactive chat interface where users interact with a simulated or live RAG assistant while Hearsay runs in real time as an inline verification middleware. Every generated claim is intercepted, decomposed into claims, verified against retrieved evidence chunks via local DeBERTa NLI cross-encoders, and decorated with real-time groundedness badges with an expandable evidence inspection drawer.

---

## 2. Goals, Non-Goals & Anti-Goals

### Goals
- **Interactive Live Demonstration:** Provide a real-time conversational chat interface within the existing React dashboard (`http://localhost:5173`) that calls Hearsay Gateway (`http://localhost:8000`).
- **Dual-Mode Reliability (Safety for Viva):**
  - **Mode A (Benchmark Corpus — Default):** Instant, 100% offline-safe RAG interaction using curated questions and Wikipedia evidence chunks from Princeton's ALCE ASQA and RAGTruth datasets. Guaranteed to work during the CUSAT viva even if Wi-Fi drops.
  - **Mode B (Live LLM Gateway):** Uses `POST /v1/chat/completions` with an optional upstream LLM API key (e.g., Gemini 1.5 Flash or Groq) to demonstrate live generation and middleware interception.
- **Visual Groundedness Telemetry:**
  - Color-coded badges per message (🟢 Grounded 100%, 🔴 Hallucination Intercepted, 🟡 Ungrounded).
  - Claim-level breakdown with confidence scores and evidence spans.
  - One-click deep link to "Inspect in Trace Explorer" to inspect the raw SQLite audit record.
- **Design System Consistency:** Matches the RevenueX Porcelain aesthetic (`#FAF8F3` background, `#0C0C12` typography, concentric border radiuses, and zero AI slop).

### Non-Goals
- Building a complex custom vector database engine (e.g. Milvus/Pinecone clusters) in 48 hours.
- Cloud SaaS hosting or user authentication.
- Implementing heavy agentic frameworks (LangChain / CrewAI) that add fragility before Saturday's evaluation.

### Anti-Goals (What would make this fail)
- A demo that fails if internet connection drops during the viva presentation.
- Hardcoded fake verification scores or synthetic mock badges that do not hit `http://localhost:8000/verify` or SQLite `hearsay_traces.db`.
- Complex multi-window setups that confuse evaluators.

---

## 3. Approaches Considered & Trade-Off Analysis

| Criteria | Approach 1: Integrated Offline-Only Tab | Approach 2: Live External LLM Only | Approach 3: Dual-Mode Companion (Selected) |
|---|---|---|---|
| **Viva Safety** | 100% Offline-safe | High risk of network/quota failure | **100% Offline-safe default** |
| **Generative Flexibility** | Curated questions only | Any arbitrary prompt | **Both arbitrary prompts & curated questions** |
| **External Dependencies** | Zero | Requires active API key & network | **Zero required (API key is optional)** |
| **Complexity** | ~180 lines frontend | ~120 lines frontend, backend proxy | **~240 lines frontend, clean state toggle** |

**Selection Rationale:** The user selected **Approach 3**. It gives complete peace of mind during the Saturday viva: the default mode works offline with real benchmark questions (ASQA, RAGTruth), while a toggle allows live generation if network is stable.

---

## 4. Architecture & Technical Specification

```
┌────────────────────────────────────────────────────────────────────────┐
│                        React SPA (Port 5173)                           │
│                                                                        │
│  ┌──────────────────────────────┐    ┌──────────────────────────────┐  │
│  │     RAG Chat Conversation    │    │   Hearsay Inspection Drawer  │  │
│  │                              │    │                              │  │
│  │ [User Query]                 │    │  Request ID: #req-9f2a8c     │  │
│  │ "Who won the 2022 World Cup?"│    │  Groundedness: 100% 🟢       │  │
│  │                              │    │                              │  │
│  │ [Assistant + Badge]          │───►│  Claims:                     │  │
│  │ "Argentina won the cup [1]." │    │  1. "Argentina won..."       │  │
│  │ 🟢 Grounded [Inspect]        │    │     Evidence: "Argentina..." │  │
│  └──────────────┬───────────────┘    │     NLI Entailment: 0.98     │  │
│                 │                    └──────────────────────────────┘  │
└─────────────────┼──────────────────────────────────────────────────────┘
                  │
                  ▼ HTTP POST /verify or /v1/chat/completions
┌────────────────────────────────────────────────────────────────────────┐
│                    FastAPI Gateway (Port 8000)                         │
│                                                                        │
│   1. Claim Decomposer (spaCy Rule-based parser)                        │
│   2. NLI Cross-Encoder (DeBERTa-v3-small in RAM)                       │
│   3. SQLite TraceStore (hearsay_traces.db)                             │
└────────────────────────────────────────────────────────────────────────┘
```

### Component Breakdown
1. **Frontend (`hearsay/frontend/src/components/RAGCompanionView.tsx`)**:
   - Split layout: Chat timeline on the left (60%), live Telemetry & Evidence Inspector on the right (40%).
   - Presets selector:
     - Preset 1: *Faithful RAG (ASQA EMNLP 2023)* — Shows verified grounded generation.
     - Preset 2: *Hallucinated RAG (RAGTruth ACL 2024)* — Shows intercepted hallucination flagged with contradiction.
     - Preset 3: *Adversarial Epistemic Evasion* — Shows hedged sentence sanitized and caught.
     - Preset 4: *Custom Query* — Allows typing arbitrary text and context.
   - Mode Toggle: "Curated Benchmark" vs "Live LLM Proxy" (reads `VITE_GEMINI_API_KEY` or falls back to prompt echo).
2. **Main Navigation Update (`App.tsx`)**:
   - Add new tab `'companion'` with a message-circle icon under `Main` navigation.
   - Deep-linking: clicking "Inspect in Trace Explorer" switches `activeTab` to `'traces'` with that trace pre-filtered.
3. **Backend (`hearsay/proxy/gateway.py`)**:
   - Existing endpoints `/verify` and `/v1/chat/completions` already support full context extraction, DeBERTa evaluation, and SQLite logging.
   - Ensure an optional helper endpoint or parameter allows clean retrieval context passing.

---

## 5. What is Left to the Builder
- Construct `RAGCompanionView.tsx` adhering to `/better-ui` (exact `0.96` active scale, `motion-safe` transitions, concentric border radiuses, no generic AI styling).
- Wire navigation in `App.tsx` and types in `types.ts`.
- Verify production build with `npm run build` (zero errors).
- Verify end-to-end integration with live gateway on port 8000.
