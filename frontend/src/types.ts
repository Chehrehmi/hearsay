export type ClaimStatus = "Supported" | "Contradicted" | "Ungrounded";

export interface NliLogits {
  entailment: number;
  neutral: number;
  contradiction: number;
}

export interface ClaimRecord {
  claim_id: number;
  claim_text: string;
  text?: string;
  status: ClaimStatus | string;
  confidence: number; // 0.0 to 1.0
  evidence_span?: string | null;
  evidence?: string | null;
  source_chunk_id?: string | null;
  nli_logits?: NliLogits | null;
}

export interface VerificationResult {
  request_id: string;
  overall_status: "Verified" | "Hallucination Detected" | string;
  grounded?: boolean;
  groundedness_score: number;
  total_claims: number;
  supported_claims: number;
  contradicted_claims: number;
  ungrounded_claims: number;
  claims: ClaimRecord[];
  latency_ms: number;
}

export interface TraceRecord {
  request_id: string;
  timestamp: string;
  source_id: string;
  response_text: string;
  overall_status: string;
  grounded?: boolean;
  groundedness_score: number;
  latency_ms: number;
  total_claims?: number;
  supported_claims?: number;
  contradicted_claims?: number;
  ungrounded_claims?: number;
  claims?: ClaimRecord[];
  result?: VerificationResult;
}

export interface MetricSummary {
  total_requests: number;
  total_verified: number;
  total_hallucinations: number;
  verification_pass_rate: number;
  avg_groundedness_score: number;
  total_claims: number;
  total_supported: number;
  total_contradicted: number;
  total_ungrounded: number;
  avg_latency_ms: number;
  p50_latency_ms?: number;
  p95_latency_ms?: number;
  p99_latency_ms?: number;
}

export interface CuratedCorpusItem {
  id: string;
  title: string;
  dataset: string;
  category: string;
  question: string;
  context: string;
  expected_response: string;
  expected_verdict?: string;
  notes?: string;
}

export interface RAGChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: string;
  contextUsed?: string;
  verification?: VerificationResult | null;
  isLoading?: boolean;
}
