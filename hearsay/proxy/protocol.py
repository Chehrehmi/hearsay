"""
hearsay.proxy.protocol: Universal Pydantic data schemes for Hearsay verification requests and results.

"""



from typing import List, Optional, Dict
from pydantic import BaseModel, Field

class ContextPayload(BaseModel):
    """Retrieved reference context/documents to verify LLM responses against."""
    source_id: str = Field(..., description="Unique identifier for the source document or chunk")
    source_info: str = Field(..., description="Raw text or concatenated chunks used as reference evidence")

class VerificationRequest(BaseModel):
    """ Incoming request payload for /verify and OpenAI-compatible proxy endpoints. """
    model: str = Field(default="gpt-3.5-turbo",description="Target model name")
    messages: List[Dict[str,str]] = Field(default_factory=list,description="OpenAI-format coversation history")
    response_text: Optional[str] = Field(default=None, description="Pre-generated LLM response to verify")
    verirag_context: Optional[ContextPayload] = Field(default=None,description="Retrieved context document payload")

class ClaimVerdict(BaseModel):
    """ Verification verdict for a single decomposed sentence/claim."""
    claim_id: int = Field(...,description="0-indexed sentence/claim sequence number")
    claim_text: str = Field(...,description="Atomic decomposed sentence or claim text")
    status: str = Field(..., description=" 'Supported', 'Unsupported (Contradiction)', 'Unsupported (Ungrounded)' ")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score between 0.0 and 1.0")
    evidence_span: Optional[str] = Field(default=None,description="Specific sentence retrieved from context as proof")
    source_chunk_id: Optional[str] = Field(default=None,description="ID of chunk containing evidence")
    nli_logits: Dict[str, float] = Field(default_factory=dict,description="Raw NLI probabilities")

class VerificationResult(BaseModel):
    """ Complete end-to-end verification pipeline output."""
    request_id: str = Field(..., description="Unique UUID trace ID")
    overall_status: str = Field(..., description=" 'Verified' or 'Hallucination Detected'")
    groundedness_score: float = Field(..., ge=0.0,le=100.0, description="Percentage of supported claims (0-100)")
    total_claims: int = Field(..., ge=0, description="Total number of evaluated claims")
    supported_claims: int=Field(...,ge=0,description="Count of supported claims")
    contradicted_claims: int = Field(...,ge=0, description="Count of contradicted claims")
    ungrounded_claims: int = Field(...,ge=0,description="Count of ungrounded claims")
    claims: List[ClaimVerdict] = Field(default_factory=list,description="Detailed list of claim verdicts")
    latency_ms: float=Field(...,description="Total pipeline latency in milliseconds")
