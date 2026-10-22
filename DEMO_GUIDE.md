# 🎙️ Hearsay 2-Minute Live Demo Guide

This script is designed for presenting Hearsay to evaluation committees, faculty guides, or project reviewers. It demonstrates the live system end-to-end in under two minutes.

---

## ⏱️ Timeline & Presentation Flow

| Time | Stage | Action |
|---|---|---|
| **0:00 - 0:30** | **The Problem & Value** | Explain why RAG systems hallucinate and why proxy-level verification is needed. |
| **0:30 - 0:50** | **Docker One-Command Boot** | Demonstrate booting the Gateway (`:8000`) and Dashboard (`:8501`) via Docker. |
| **0:50 - 1:25** | **Live Proxy Verification** | Fire a test request with an uncited hallucinated sentence and show immediate detection. |
| **1:25 - 2:00** | **Observability Dashboard** | Show the Streamlit UI, green/yellow/red claim cards, latency telemetry, and live sandbox. |

---

## Step 1: Boot the Entire Stack (20 seconds)

Open a terminal and run:

```bash
docker compose up -d
```

Verify that both services are healthy:

```bash
docker compose ps
```

> **What to Say:**  
> *"Hearsay is completely containerized. With a single `docker compose up` command, we spin up two decoupled services: an OpenAI-compatible FastAPI verification proxy on port 8000, and a real-time Streamlit observability dashboard on port 8501, both sharing an indexed SQLite audit store."*

---

## Step 2: Live Proxy Verification via CLI (35 seconds)

Run a test request containing one supported claim and one completely ungrounded hallucination:

```bash
curl -X POST http://localhost:8000/verify \
  -H "Content-Type: application/json" \
  -d '{
    "response_text": "Apollo 11 landed on the Moon in 1969. Commander Neil Armstrong walked on Mars in 1975.",
    "verirag_context": {
      "source_id": "wiki_apollo11",
      "source_info": "Apollo 11 was the American spaceflight that first landed humans on the Moon on July 20, 1969. Neil Armstrong was the first person to walk on the lunar surface."
    }
  }'
```

### Key Highlights in the Response:
1. Point to `"overall_status": "Hallucination Detected"` and `"groundedness_score": 50.0`.
2. Point to **Claim 0** (`"Apollo 11 landed on the Moon in 1969"`):
   - Status: `Supported` (Confidence: 0.95)
   - Evidence Span: `"Apollo 11 was the American spaceflight that first landed humans on the Moon on July 20, 1969."`
3. Point to **Claim 1** (`"Commander Neil Armstrong walked on Mars in 1975"`):
   - Status: `Unsupported (Ungrounded)`
   - Evidence Span: `null`

> **What to Say:**  
> *"Notice that instead of evaluating the whole paragraph as a black box, Hearsay decomposed the output into two atomic sentences. It verified that the Moon landing is factually grounded in the retrieved document, but caught that the Mars walk claim is an uncited hallucination, returning a 50% groundedness score in milliseconds."*

---

## Step 3: Streamlit Observability Dashboard (35 seconds)

Open [http://localhost:8501](http://localhost:8501) in your browser.

### Tour Highlights:
1. **Top KPI Banner:**
   - Point out **Total Requests**, **Pass Rate**, **Average Groundedness**, and **P50 / P95 Latency** metrics (reading live from SQLite).
2. **Tab 1: Trace Explorer & Evidence Map:**
   - Select the trace we just fired (`a1b2c3d4...`).
   - Point out the color-coded verdict cards:
     - 🟢 **Green Card:** Supported claim with the exact retrieved text span.
     - 🟡 **Yellow Card:** Ungrounded claim alerting the user that no evidence was found.
   - Point out the **🎯 Retrieval Diagnostics** card showing the Context Utilization Rate.
3. **Tab 2: Live Verification Sandbox:**
   - Type or modify a custom claim directly in the browser and click **"🚀 Verify Groundedness"** to show instant live verification without writing any code.
4. **Tab 3: Reliability & Latency Analytics:**
   - Point out the Request Latency Trend line chart and claim distribution bar charts.

> **What to Say:**  
> *"Downstream AI engineers and auditors don't just want a pass/fail flag; they need explainability. Our dashboard highlights the exact evidence spans in green, warns on context gaps in yellow, and tracks P95 tail latencies to ensure inference doesn't degrade user experience."*

---

## Step 4: Verification of Test Suite (10 seconds)

In your terminal, run the automated test suite:

```bash
pytest -v
```

> **What to Say:**  
> *"All 86 automated unit, integration, and headless UI tests pass with 100% reliability, covering the protocol models, database percentiles, proxy gateway, and Streamlit components."*

---

## Clean Up

When concluding the demo:

```bash
docker compose down
```
