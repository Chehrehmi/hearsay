import os
os.environ.setdefault("HF_HUB_OFFLINE", "1")
import threading
import uuid
import time
from pathlib import Path
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, HTTPException, Request, Response, Depends, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from starlette.concurrency import run_in_threadpool

from hearsay.proxy import ContextPayload
from hearsay.proxy.protocol import VerificationRequest, VerificationResult, ClaimVerdict
from hearsay.db import TraceStore

app = FastAPI(
    title="Hearsay Gateway API",
    version="0.1.0-mvp",
    description="OpenAI-compatible verification proxy for RAG groundedness"
)

# Enable CORS for browser frontend (React / Vite)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:8000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Default production database instance
_default_trace_store = TraceStore()

def get_trace_store() -> TraceStore:
    """Dependency provider returning the active TraceStore instance."""
    return _default_trace_store


@app.get("/health")
async def health():
    return {
        "status":"healthy",
        "service":"hearsay-gateway"
    }


@app.get("/v1/demo/corpus")
async def get_demo_corpus():
    """
    Returns curated authentic benchmark scenarios from RAGTruth and ALCE
    for live RAG demonstration.
    """
    from hearsay.demo.corpus import get_curated_rag_samples
    return get_curated_rag_samples()

@app.post("/verify",response_model=VerificationResult)
async def verify_response(
    req: VerificationRequest, 
    request: Request,
    db: TraceStore = Depends(get_trace_store)
):
    # 1. Validate response_text
    response_text = (req.response_text or req.response or "").strip()
    if not response_text:
        raise HTTPException(status_code=400, detail="Field 'response_text' is required and cannot be empty.")
    


    # 2. Extract Context (from body OR headers)
    context = _extract_context(request, req.verirag_context, req.context)

    if not context:
        raise HTTPException(
            status_code=400,
            detail="Verification context is required either in 'verirag_context' body or via 'X-Hearsay-Context' header. "
        )

    # 3. Execute Verification & return 
    result = await run_in_threadpool(_execute_verification, response_text, context)
    # 4. Automatically log trace to audit store (Day 4 Feature)
    db.log_trace(result, response_text, context.source_id)
    
    return result


GREETINGS = {
    "hi", "hello", "hey", "good morning", "good evening", "good afternoon",
    "greetings", "hi there", "hello there", "howdy", "sup", "yo"
}


async def _generate_rag_completion(
    messages: List[Dict[str, str]],
    context: Optional[ContextPayload],
    request: Request,
    model: str = "gemini-2.5-flash",
) -> str:
    """
    Generates assistant completion via any OpenAI-compatible API provider,
    or returns benchmark responses when explicitly in benchmark mode.
    Never falls back to random historical context when API keys are missing.
    """
    from hearsay.proxy.settings_store import SettingsStore
    last_user_msg = messages[-1].get("content", "").strip() if messages else ""

    # 1. Clean conversational greeting handling without context
    if last_user_msg.lower().strip("!?. ") in GREETINGS and (not context or not context.source_info.strip()):
        return (
            "Hello! I am Hearsay, your RAG verification companion. "
            "Upload a PDF or select an adversarial question below to begin testing real-time groundedness."
        )

    # 2. Offline benchmark mode (deterministic ground truth from curated corpus)
    if model == "hearsay-verified":
        if context and context.source_info:
            from hearsay.demo.corpus import get_curated_rag_samples
            samples = {s["id"]: s for s in get_curated_rag_samples()}
            if context.source_id in samples:
                return samples[context.source_id]["expected_response"]
            raw_sents = [s.strip() for s in context.source_info.split(".") if len(s.strip()) > 8]
            if raw_sents:
                return ". ".join(raw_sents[:2]) + "."
        return f"Verified benchmark answer regarding: {last_user_msg}"

    # 3. Live model generation
    provider = (request.headers.get("x-provider") or "gemini").lower()
    api_key = (
        request.headers.get("x-api-key")
        or request.headers.get("x-gemini-key")
        or SettingsStore().get_api_key(provider)
        or os.environ.get("GEMINI_API_KEY")
        or os.environ.get("GOOGLE_API_KEY")
    )

    if not api_key or not api_key.strip():
        raise HTTPException(
            status_code=400,
            detail=f"{provider.capitalize()} API key is not configured. Please add your key in Settings.",
        )

    try:
        import json
        import urllib.request as _urllib_req

        ctx_text = context.source_info if context else "No context provided."
        system_prompt = (
            "You are an enterprise RAG assistant. Answer the user's question "
            "accurately using ONLY the following reference context.\n\n"
            f"Context: {ctx_text}\n\nUser Question: {last_user_msg}"
        )

        if provider == "gemini":
            model_target = request.headers.get("x-gemini-model") or "gemini-2.5-flash"
            url = (
                f"https://generativelanguage.googleapis.com/v1beta/models/"
                f"{model_target}:generateContent?key={api_key.strip()}"
            )
            prompt_payload = {
                "contents": [{"parts": [{"text": system_prompt}]}],
                "generationConfig": {"temperature": 0.2, "maxOutputTokens": 300},
            }
            req_data = json.dumps(prompt_payload).encode("utf-8")
            http_req = _urllib_req.Request(
                url, data=req_data, headers={"Content-Type": "application/json"}
            )
            with _urllib_req.urlopen(http_req, timeout=15) as resp:
                result_json = json.loads(resp.read().decode("utf-8"))
                candidates = result_json.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts and "text" in parts[0]:
                        return parts[0]["text"].strip()
                raise ValueError("No candidates returned from Gemini API.")

        else:
            # OpenAI-compatible endpoint (openai, groq, custom)
            store = SettingsStore()
            if provider == "custom":
                base_url = store.get_base_url("custom") or "https://api.openai.com/v1"
            elif provider == "openai":
                base_url = "https://api.openai.com/v1"
            elif provider == "groq":
                base_url = "https://api.groq.com/openai/v1"
            else:
                base_url = "https://api.openai.com/v1"

            model_target = request.headers.get("x-model") or "gpt-4o-mini"
            url = f"{base_url.rstrip('/')}/chat/completions"
            payload = {
                "model": model_target,
                "messages": [{"role": "user", "content": system_prompt}],
                "temperature": 0.2,
                "max_tokens": 300,
            }
            req_data = json.dumps(payload).encode("utf-8")
            http_req = _urllib_req.Request(
                url,
                data=req_data,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key.strip()}",
                },
            )
            with _urllib_req.urlopen(http_req, timeout=15) as resp:
                result_json = json.loads(resp.read().decode("utf-8"))
                return result_json["choices"][0]["message"]["content"].strip()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"Upstream {provider} call failed: {str(e)}. Check your API key and network.",
        )


@app.post("/v1/chat/completions")
@app.post("/v1/chat/completions/")
@app.post("/api/chat/completions")
@app.post("/api/chat/completions/")
async def chat_completions(
    req: VerificationRequest,
    request: Request,
    response: Response,
    db: TraceStore = Depends(get_trace_store)
) -> Dict[str, Any]:
    # 1. Extract context (from body or headers)
    context = _extract_context(request, req.verirag_context, req.context)

    # Detect conversational greetings without document context
    last_msg = req.messages[-1].get("content", "").strip() if req.messages else ""
    is_greeting = (
        last_msg.lower().strip("!?. ") in GREETINGS
        and (not context or not context.source_info.strip())
    )

    # 2. Determine assistant completion text
    if req.response_text and req.response_text.strip():
        generated_text = req.response_text.strip()
    elif req.response and req.response.strip():
        generated_text = req.response.strip()
    elif req.messages:
        generated_text = await _generate_rag_completion(req.messages, context, request, model=req.model)
    else:
        generated_text = "Hearsay proxy default response."

    # If adversarial perturbation requested, apply epistemic hedging
    if req.adversarial and generated_text and not is_greeting:
        try:
            from hearsay.eval.adversarial_attacks import apply_adversarial_attack
            generated_text = apply_adversarial_attack(generated_text, "hedging")
        except Exception:
            pass

    # 3. Perform verification if context is present and NOT a simple greeting
    verification = None
    if context and context.source_info.strip() and not is_greeting:
        verification = await run_in_threadpool(_execute_verification, generated_text, context)
        # Inject observability headers into HTTP response
        response.headers["X-Hearsay-Status"] = verification.overall_status
        response.headers["X-Hearsay-Score"] = str(verification.groundedness_score)
        response.headers["X-Hearsay-Request-ID"] = verification.request_id

        # Automatically log trace to audit store (Day 4 Feature)
        db.log_trace(verification, generated_text, context.source_id)
    else:
        response.headers["X-Hearsay-Status"] = "Unverified (No Context)"

    # 4. Build OpenAI-compatible response payload
    created_ts = int(time.time())
    completion_id = f"chatcmpl-{uuid.uuid4().hex[:12]}"
    prompt_tokens = sum(len(m.get("content", "").split()) for m in req.messages)
    completion_tokens = len(generated_text.split())

    openai_payload: Dict[str, Any] = {
        "id": completion_id,
        "object": "chat.completion",
        "created": created_ts,
        "model": req.model,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": generated_text,
                },
                "finish_reason": "stop"
            }
        ],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens
        }
    }

    # 5. Enrich body with verification telemetry
    if verification:
        openai_payload["hearsay_verification"] = verification.model_dump()

    return openai_payload

@app.get("/v1/traces")
async def list_traces(
    limit: int = 50,
    offset: int = 0,
    status_filter: Optional[str] = None,
    db: TraceStore = Depends(get_trace_store),
) -> List[Dict[str, Any]]:
    """
    Retrieve historical verification traces with pagination and optional status filtering.
    """
    return db.get_recent_traces(limit=limit, offset=offset, status_filter=status_filter)


@app.get("/v1/traces/{request_id}")
async def get_trace_detail(
    request_id: str,
    db: TraceStore = Depends(get_trace_store),
) -> Dict[str, Any]:
    """
    Retrieve full audit trace details for a specific request ID.
    Returns 404 if the trace does not exist.
    """
    trace = db.get_trace(request_id)
    if not trace:
        raise HTTPException(
            status_code=404,
            detail=f"Trace with request_id '{request_id}' not found."
        )
    return trace


@app.get("/v1/metrics")
async def get_metrics_summary(
    db: TraceStore = Depends(get_trace_store),
) -> Dict[str, Any]:
    """
    Retrieve aggregated verification performance and reliability metrics.
    """
    return db.get_metrics_summary()


@app.post("/v1/settings")
@app.post("/v1/settings/")
@app.post("/api/settings")
@app.post("/api/settings/")
@app.post("/api/settings/keys")
@app.post("/api/settings/keys/")
async def save_settings(body: Dict[str, str]) -> Dict[str, Any]:
    """
    Persist an API key for a given provider to the local .env file.
    Supported providers: gemini, openai, groq, custom.
    The key is stored server-side and never returned after save.
    Optional 'base_url' field is honoured for the 'custom' provider.
    """
    from hearsay.proxy.settings_store import SettingsStore, SUPPORTED_PROVIDERS
    provider = body.get("provider", "").strip().lower()
    api_key = body.get("api_key", "").strip()
    base_url = body.get("base_url", "").strip() or None

    if provider not in SUPPORTED_PROVIDERS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported provider '{provider}'. Choose from: {sorted(SUPPORTED_PROVIDERS)}",
        )
    if not api_key:
        raise HTTPException(status_code=400, detail="api_key must not be empty.")

    SettingsStore().save_api_key(provider, api_key, base_url=base_url)
    return {"saved": True, "provider": provider}


@app.get("/v1/settings/status")
@app.get("/v1/settings/status/")
@app.get("/api/settings/status")
@app.get("/api/settings/status/")
async def get_settings_status() -> Dict[str, bool]:
    """
    Returns {provider: is_configured} for all supported providers.
    Never returns the key values themselves.
    """
    from hearsay.proxy.settings_store import SettingsStore
    return SettingsStore().get_status()


# In-memory store for uploaded PDF text: source_id -> extracted text
_pdf_store: Dict[str, str] = {}


@app.get("/v1/rag/adversarial-bank")
@app.get("/v1/rag/adversarial-bank/")
@app.get("/api/rag/adversarial-bank")
@app.get("/api/rag/adversarial-bank/")
@app.get("/api/adversarial-bank")
@app.get("/api/adversarial-bank/")
async def get_adversarial_bank_endpoint():
    """
    Returns the 10-question adversarial test bank for the Minimal RAG Companion demo.
    Questions are designed to induce parametric memory conflicts with the
    counterfactual medical guidelines PDF.
    """
    from hearsay.demo.adversarial_questions import get_adversarial_bank
    return get_adversarial_bank()


@app.post("/v1/rag/upload")
@app.post("/v1/rag/upload/")
@app.post("/api/upload")
@app.post("/api/upload/")
@app.post("/api/rag/upload")
@app.post("/api/rag/upload/")
async def upload_pdf(file: UploadFile = File(...)) -> Dict[str, Any]:
    """
    Accepts a PDF upload, extracts text via pdfplumber (pypdf fallback),
    stores in memory keyed by a generated source_id, and returns metadata.
    The source_id can then be used as verirag_context.source_id in chat completions.
    """
    import uuid as _uuid

    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Empty file — please upload a non-empty PDF.")

    extracted = ""

    # Primary: pdfplumber
    try:
        import pdfplumber, io
        with pdfplumber.open(io.BytesIO(raw)) as pdf:
            extracted = "".join(p.extract_text() or "" for p in pdf.pages)
    except Exception:
        pass

    # Fallback: pypdf
    if not extracted.strip():
        try:
            import pypdf, io
            reader = pypdf.PdfReader(io.BytesIO(raw))
            extracted = "".join(
                page.extract_text() or "" for page in reader.pages
            )
        except Exception:
            pass

    if len(extracted.strip()) < 20:
        raise HTTPException(
            status_code=400,
            detail="Could not extract readable text from the PDF. "
                   "Ensure the file is not image-only or password-protected.",
        )

    source_id = f"upload-{_uuid.uuid4().hex[:8]}"
    _pdf_store[source_id] = extracted.strip()

    return {
        "source_id": source_id,
        "filename": file.filename or "uploaded.pdf",
        "preview": extracted.strip()[:200],
        "char_count": len(extracted.strip()),
    }


@app.post("/v1/traces/clear")
@app.delete("/v1/traces")
async def clear_all_traces(
    db: TraceStore = Depends(get_trace_store),
) -> Dict[str, Any]:
    """
    Clears all stored traces in the audit database.
    Enables instant reset of live telemetry for demonstration and evaluation sessions.
    """
    deleted_count = db.clear_traces()
    return {"status": "ok", "deleted_traces": deleted_count}


_engine_singleton = None
_engine_lock = threading.Lock()

def _get_engine():
    global _engine_singleton
    if _engine_singleton is None:
        with _engine_lock:
            if _engine_singleton is None:
                from hearsay.engine.pipeline import HearsayEngine
                _engine_singleton = HearsayEngine()
    return _engine_singleton


@app.on_event("startup")
async def warmup_engine():
    """Pre-warm the ML verification engine in background thread so first request has zero cold-start delay."""
    import logging
    try:
        threading.Thread(target=_get_engine, daemon=True).start()
        logging.info("HearsayEngine background warmup dispatched.")
    except Exception as e:
        logging.warning(f"Engine warmup dispatch failed: {e}")


def _execute_verification(response_text:str,context:ContextPayload)->VerificationResult:
    """
    Executes verification using HearsayEngine singleton if available, otherwise uses a deterministic fallback.
    """
    start_time=time.perf_counter()
    try:
        engine = _get_engine()
        raw_result = engine.verify(response_text, context.source_info, source_id=context.source_id)
        return VerificationResult.model_validate(raw_result)
    except Exception as e:
        import logging
        logging.warning(f"HearsayEngine unavailable or error: {e}. Using deterministic fallback.")
        # Deterministic lightweight fallback for Day 2 testing / offline testing:
        # Split into sentences ( by period)
        sentences=[s.strip() for s in response_text.split(".") if len(s.strip()) >3 ]
        if not sentences:
            sentences=[response_text.strip()]
        claims=[]
        supported_count=0
        ungrounded_count=0

        for idx,sentence in enumerate(sentences):
            # Check if sentence exists or overlaps in source_info
            is_supported = sentence.lower() in context.source_info.lower()
            status="Supported" if is_supported else "Unsupported (Ungrounded)"
            confidence=0.95 if is_supported else 0.80

            if is_supported:
                supported_count+=1
            else:
                ungrounded_count+=1
            claims.append(
                ClaimVerdict(
                    claim_id=idx,
                    claim_text=sentence,
                    status=status,
                    confidence=confidence,
                    evidence_span=context.source_info if is_supported else None,
                    source_chunk_id=context.source_id if is_supported else None
                )
            )
        total = len(claims)
        groundedness = round((supported_count/total*100.0) if total>0 else 0.0,2)
        elapsed_ms = round((time.perf_counter() - start_time)*1000,2)
        return VerificationResult(
            request_id=str(uuid.uuid4())[:8],
            overall_status="Verified" if ungrounded_count==0 else "Hallucination Detected",
            groundedness_score=groundedness,
            total_claims=total,
            supported_claims=supported_count,
            contradicted_claims=0,
            ungrounded_claims=ungrounded_count,
            claims=claims,
            latency_ms=elapsed_ms
        )


def _extract_context(
    request: Request,
    body_context: Optional[ContextPayload] = None,
    alt_context: Optional[Any] = None
) -> Optional[ContextPayload]:
    """
    Extracts verification context from request body (Priority 1),
    uploaded PDF store (Priority 1b — when source_id matches an upload),
    or HTTP headers (Priority 2).
    """
    # 1. Check body (standard — source_info provided directly)
    if body_context and body_context.source_info.strip():
        return body_context

    # 1b. Body has a source_id that matches an uploaded PDF
    if body_context and body_context.source_id and body_context.source_id in _pdf_store:
        return ContextPayload(
            source_id=body_context.source_id,
            source_info=_pdf_store[body_context.source_id],
        )

    # 1c. Check body (list or dict fallback)
    if alt_context:
        if isinstance(alt_context, list) and len(alt_context) > 0:
            first = alt_context[0]
            if isinstance(first, dict):
                s_id = str(first.get("id") or first.get("source_id") or "doc_user_input")
                s_info = str(first.get("text") or first.get("source_info") or "").strip()
                if s_info:
                    return ContextPayload(source_id=s_id, source_info=s_info)
                # Check pdf store for this source_id
                if s_id in _pdf_store:
                    return ContextPayload(source_id=s_id, source_info=_pdf_store[s_id])
        elif isinstance(alt_context, dict):
            s_id = str(alt_context.get("id") or alt_context.get("source_id") or "doc_user_input")
            s_info = str(alt_context.get("text") or alt_context.get("source_info") or "").strip()
            if s_info:
                return ContextPayload(source_id=s_id, source_info=s_info)
            if s_id in _pdf_store:
                return ContextPayload(source_id=s_id, source_info=_pdf_store[s_id])

    # 2. Check HTTP headers
    header_context = request.headers.get("x-hearsay-context") or request.headers.get("x-verirag-context")
    if header_context and header_context.strip():
        source_id = (
            request.headers.get("x-hearsay-source-id")
            or request.headers.get("x-verirag-source-id")
            or "header_source"
        )
        return ContextPayload(source_id=source_id, source_info=header_context.strip())

    return None


# Mount static React SPA if built
from fastapi.staticfiles import StaticFiles

frontend_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")


def main():
    """Run the Hearsay Gateway server with uvicorn."""
    import uvicorn
    import argparse

    parser = argparse.ArgumentParser(description="Hearsay Gateway Server")
    parser.add_argument("--host", default="0.0.0.0", help="Bind host (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8000, help="Bind port (default: 8000)")
    parser.add_argument("--reload", action="store_true", help="Enable reload")
    args, _ = parser.parse_known_args()

    uvicorn.run("hearsay.proxy.gateway:app", host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()
