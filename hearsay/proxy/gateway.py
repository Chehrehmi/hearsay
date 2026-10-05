from hearsay.proxy import ContextPayload
import uuid
import time
from fastapi import FastAPI,HTTPException, Request, Response
from hearsay.proxy.protocol import VerificationRequest,VerificationResult,ClaimVerdict
from typing import Optional, Dict, Any

app = FastAPI(
    title="Hearsay Gateway API",
    version="0.1.0-mvp",
    description="OpenAI-compatible verification proxy for RAG groundedness"
)

@app.get("/health")
async def health():
    return {
        "status":"healthy",
        "service":"hearsay-gateway"
    }

@app.post("/verify",response_model=VerificationResult)
async def verify_response(req:VerificationRequest, request:Request):
    # 1. Validate response_text
    if not req.response_text or not req.response_text.strip():
        raise HTTPException(status_code=400,detail="Field 'response_text' is required and cannot be empty.")
    


    # 2. Extract Context (from body OR headers)
    context = _extract_context(request,req.verirag_context)

    if not context:
        raise HTTPException(
            status_code=400,
            detail="Verification context is required either in 'verirag_context' body or via 'X-Hearsay-Context' header. "
        )

    # 3. Execute Verification & return 
    return _execute_verification(req.response_text,context)


@app.post("/v1/chat/completions")
async def chat_completions(req:VerificationRequest,request:Request,response:Response)->Dict[str,Any]:
    # 1. Determine assistant completion text
    # (If caller passed response_text, verify it; otherwise use the last user message or sample answer)
    if req.response_text and req.response_text.strip():
        generated_text = req.response_text.strip()
    elif req.messages:
        last_user_msg=req.messages[-1].get("content","")
        generated_text=f"Verified answer regarding:{last_user_msg}"
    else:
        generated_text="Hearsay proxy default response."
    
    # 2. Extract content (from body or headers)
    context = _extract_context(request,req.verirag_context)

    # 3. Perform verification if context is present
    verification = None
    if context:
        verification = _execute_verification(generated_text,context)
        # Inject observability headers into HTTP response
        response.headers["X-Hearsay-Status"] = verification.overall_status
        response.headers["X-Hearsay-Score"] = str(verification.groundedness_score)
        response.headers["X-Hearsay-Request-ID"]=verification.request_id
    else:
        response.headers["X-Hearsay-Status"]="Unverified (No Context)"
    # 4. Build OpenAI-compatible response payload
    created_ts = int(time.time())
    completion_id=f"chatcmpl-{uuid.uuid4().hex[:12]}"
    prompt_tokens= sum(len(m.get("content","").split()) for m in req.messages)
    completion_tokens = len(generated_text.split())

    openai_payload: Dict[str,Any] = {
        "id":completion_id,
        "object":"chat.completion",
        "created":created_ts,
        "model":req.model,
        "choices":[
            {
                "index":0,
                "message":{
                    "role":"assistant",
                    "content":generated_text,
                },
                "finish_reason":"stop"
            }
        ],
        "usage":{
            "prompt_tokens":prompt_tokens,
            "completion_tokens":completion_tokens,
            "total_tokens":prompt_tokens+completion_tokens
        }
    }
    # 5. Enrich body with verificaiton telemetry
    if verification:
        openai_payload["hearsay_verification"]=verification.model_dump()
    return openai_payload

def _execute_verification(response_text:str,context:ContextPayload)->VerificationResult:
    """
    Executes verification using HearsayEngine if available, otherwise uses a deterministic fallback.
    """
    start_time=time.perf_counter()
    # Try using Akhil's engine if its installed/available
    try:
        # pyrefly: ignore [missing-import]
        from hearsay.engine.pipeline import HearsayEngine
        engine=HearsayEngine()
        raw_result=engine.verify(response_text,context.source_info)
        return VerificationResult.model_validate(raw_result)
    except (ImportError,Exception):
        # Deterministic lightweight fallback for Day 2 testing:
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


def _extract_context(request:Request, body_context:Optional[ContextPayload]=None)->Optional[ContextPayload]:
    """
    Extracts verification context from request body (Priority 1) 
                                   or 
    HTTP headers (Priority 2: X-Hearsay-Context / X-VeriRAG-Context).
    """
    # 1. Check body
    if body_context and body_context.source_info.strip():
        return body_context
    
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