import os
os.environ.setdefault("HF_HUB_OFFLINE", "1")
import threading
import uuid
import time
from pathlib import Path
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, HTTPException, Request, Response, Depends
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


async def _generate_rag_completion(
    messages: List[Dict[str, str]],
    context: Optional[ContextPayload],
    request: Request,
) -> str:
    """
    Generates assistant completion either via live Gemini API (if key provided)
    or via offline context extraction.
    """
    last_user_msg = messages[-1].get("content", "") if messages else "Summary request"
    gemini_key = request.headers.get("x-gemini-key") or os.environ.get("GEMINI_API_KEY")

    # 1. Live Gemini Generation (if API key available)
    if gemini_key and gemini_key.strip():
        try:
            import json
            import urllib.request
            model_target = request.headers.get("x-gemini-model") or "gemini-2.5-flash"
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_target}:generateContent?key={gemini_key.strip()}"
            
            ctx_text = context.source_info if context else "No context provided."
            prompt_payload = {
                "contents": [
                    {
                        "parts": [
                            {
                                "text": (
                                    f"System: You are an enterprise RAG assistant. Answer the user's question accurately "
                                    f"using ONLY the following reference context.\n\n"
                                    f"Context: {ctx_text}\n\n"
                                    f"User Question: {last_user_msg}"
                                )
                            }
                        ]
                    }
                ],
                "generationConfig": {"temperature": 0.2, "maxOutputTokens": 300}
            }
            req_data = json.dumps(prompt_payload).encode("utf-8")
            http_req = urllib.request.Request(url, data=req_data, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(http_req, timeout=10) as resp:
                result_json = json.loads(resp.read().decode("utf-8"))
                candidates = result_json.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts and "text" in parts[0]:
                        return parts[0]["text"].strip()
        except Exception as e:
            import logging
            logging.warning(f"Upstream Gemini call failed ({e}). Falling back to offline extraction.")

    # 2. Offline Extractive RAG Fallback (Zero network risk for Viva)
    if context and context.source_info:
        raw_sents = [s.strip() for s in context.source_info.split(".") if len(s.strip()) > 8]
        if raw_sents:
            return ". ".join(raw_sents[:2]) + "."

    return f"Verified answer regarding: {last_user_msg}"


@app.post("/v1/chat/completions")
async def chat_completions(
    req: VerificationRequest,
    request: Request,
    response: Response,
    db: TraceStore = Depends(get_trace_store)
) -> Dict[str, Any]:
    # 1. Extract context (from body or headers)
    context = _extract_context(request, req.verirag_context, req.context)

    # 2. Determine assistant completion text
    if req.response_text and req.response_text.strip():
        generated_text = req.response_text.strip()
    elif req.response and req.response.strip():
        generated_text = req.response.strip()
    elif req.messages:
        generated_text = await _generate_rag_completion(req.messages, context, request)
    else:
        generated_text = "Hearsay proxy default response."

    # 3. Perform verification if context is present
    verification = None
    if context:
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
    Extracts verification context from request body (Priority 1) 
                                   or 
    HTTP headers (Priority 2: X-Hearsay-Context / X-VeriRAG-Context).
    """
    # 1. Check body (standard)
    if body_context and body_context.source_info.strip():
        return body_context

    # 1b. Check body (list or dict fallback)
    if alt_context:
        if isinstance(alt_context, list) and len(alt_context) > 0:
            first = alt_context[0]
            if isinstance(first, dict):
                s_id = str(first.get("id") or first.get("source_id") or "doc_user_input")
                s_info = str(first.get("text") or first.get("source_info") or "").strip()
                if s_info:
                    return ContextPayload(source_id=s_id, source_info=s_info)
        elif isinstance(alt_context, dict):
            s_id = str(alt_context.get("id") or alt_context.get("source_id") or "doc_user_input")
            s_info = str(alt_context.get("text") or alt_context.get("source_info") or "").strip()
            if s_info:
                return ContextPayload(source_id=s_id, source_info=s_info)
    
    # 2. Check HTTP headers

    header_context = request.headers.get("x-hearsay-context") or request.headers.get("x-verirag-context")
    if header_context and header_context.strip():
        source_id = (
            request.headers.get("x-hearsay-source-id") 
            or request.headers.get("x-verirag-source-id")
            or "header_source"
        )
        return ContextPayload(source_id=source_id,source_info=header_context.strip())

    return None


# Mount static React SPA if built
from fastapi.staticfiles import StaticFiles

frontend_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")