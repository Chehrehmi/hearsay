import type { VerificationResult } from '../types';

interface HearsayDrawerProps {
  verification: VerificationResult | null;
  open: boolean;
  onClose: () => void;
  apiBase: string;
}

export function HearsayDrawer({ verification, open, onClose, apiBase }: HearsayDrawerProps) {
  const pct = verification && verification.total_claims > 0
    ? (verification.contradicted_claims / verification.total_claims) * 100
    : 0;

  const statusBg = !verification ? ''
    : verification.overall_status === 'Verified' ? 'bg-[#E8F8D6] text-[#15803D]'
    : pct > 30 ? 'bg-[#FEE2E2] text-[#991B1B]'
    : 'bg-[#FEF3C7] text-[#92400E]';

  return (
    <aside
      className={`shrink-0 border-l border-[#D9D4C7]/70 bg-white flex flex-col transition-all duration-200 ease-in-out overflow-hidden ${
        open ? 'w-[340px] xl:w-[360px]' : 'w-0'
      }`}
    >
      {open && (
        <>
          {/* Drawer header */}
          <div className="h-14 border-b border-[#D9D4C7]/70 flex items-center justify-between px-4 shrink-0">
            <span className="text-xs font-semibold text-[#0C0C12] uppercase tracking-wider">
              Hearsay Live Inspector
            </span>
            <div className="flex items-center gap-2">
              {verification && (
                <span className="text-[10px] font-mono text-[#9A9890]">
                  #{verification.request_id.slice(0, 8)}
                </span>
              )}
              <button
                type="button"
                onClick={onClose}
                className="p-1.5 rounded-lg text-[#9A9890] hover:text-[#0C0C12] hover:bg-[#F1EFEA] transition-colors"
              >
                <svg width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                  <path d="M18 6L6 18M6 6l12 12" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </button>
            </div>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {!verification ? (
              <>
                {/* Standby state */}
                <div className="flex flex-col items-center justify-center text-center py-8 space-y-2">
                  <div className="w-10 h-10 rounded-full bg-[#E8E4DA]/50 flex items-center justify-center">
                    <svg className="w-5 h-5 text-[#7A7870]" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="1.8" viewBox="0 0 24 24">
                      <path d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                  </div>
                  <p className="text-xs font-semibold text-[#0C0C12]">Verification Standby</p>
                  <p className="text-[11px] text-[#9A9890] max-w-[220px]">
                    Send a message or click any assistant response to inspect its verification trace here.
                  </p>
                </div>

                {/* Pipeline topology */}
                <div className="p-3.5 bg-[#FAF8F3] rounded-2xl border border-[#EBE7DC] space-y-2.5">
                  <span className="text-[10px] font-semibold text-[#9A9890] uppercase tracking-wider block">
                    Inline Pipeline
                  </span>
                  {[
                    { n: 1, title: 'Claim Segmentation', desc: 'Splits LLM outputs into verifiable assertions' },
                    { n: 2, title: 'DeBERTa-v3 Cross-Encoder', desc: 'Scores Entailment, Neutral & Contradiction vs context' },
                    { n: 3, title: 'Groundedness Gating', desc: 'Passes verified facts; flags hallucinations' },
                  ].map(step => (
                    <div key={step.n} className="flex items-center gap-2.5 p-2 rounded-xl bg-white border border-[#EBE7DC]">
                      <span className="w-5 h-5 rounded-full bg-[#0C0C12] text-white text-[10px] font-mono flex items-center justify-center shrink-0">
                        {step.n}
                      </span>
                      <div>
                        <div className="text-[11px] font-medium text-[#0C0C12]">{step.title}</div>
                        <div className="text-[10px] text-[#9A9890]">{step.desc}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </>
            ) : (
              <>
                {/* Verdict card */}
                <div className="bg-white border border-[#D9D4C7]/80 rounded-2xl p-4 space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-[11px] font-medium text-[#9A9890] uppercase tracking-wider">Verdict</span>
                    <span className={`px-2.5 py-0.5 rounded-full text-xs font-semibold ${statusBg}`}>
                      {verification.overall_status}
                    </span>
                  </div>

                  <div className="grid grid-cols-3 gap-2 pt-2 border-t border-[#F1EFEA] text-center">
                    {[
                      { label: 'Groundedness', value: `${verification.groundedness_score}%`, color: 'text-[#0C0C12]' },
                      { label: 'Contradiction', value: `${pct.toFixed(1)}%`, color: pct > 30 ? 'text-[#DC2626]' : pct > 0 ? 'text-[#D97706]' : 'text-[#15803D]' },
                      { label: 'Latency', value: `${verification.latency_ms}ms`, color: 'text-[#0C0C12]' },
                    ].map(stat => (
                      <div key={stat.label} className="p-2 bg-[#FAF8F3] rounded-xl border border-[#EBE7DC]">
                        <div className="text-[9px] text-[#9A9890] uppercase tracking-wide">{stat.label}</div>
                        <div className={`text-sm font-semibold font-mono tabular-nums ${stat.color}`}>{stat.value}</div>
                      </div>
                    ))}
                  </div>

                  <div className="grid grid-cols-3 gap-2 text-center text-[11px]">
                    <div><span className="text-[#15803D] font-semibold">{verification.supported_claims}</span><span className="text-[#9A9890]"> supported</span></div>
                    <div><span className="text-[#DC2626] font-semibold">{verification.contradicted_claims}</span><span className="text-[#9A9890]"> contra.</span></div>
                    <div><span className="text-[#D97706] font-semibold">{verification.ungrounded_claims}</span><span className="text-[#9A9890]"> ungrounded</span></div>
                  </div>
                </div>

                {/* Claims breakdown */}
                <div className="space-y-2">
                  <div className="text-[11px] font-semibold text-[#9A9890] uppercase tracking-wider">
                    Claims ({verification.claims.length})
                  </div>
                  {verification.claims.map(claim => {
                    const isContradiction = claim.status.toLowerCase().includes('contradict');
                    const isUngrounded = claim.status.toLowerCase().includes('ungrounded');
                    const pillColor = isContradiction ? 'bg-[#FEE2E2] text-[#991B1B]'
                      : isUngrounded ? 'bg-[#FEF3C7] text-[#92400E]'
                      : 'bg-[#E8F8D6] text-[#15803D]';

                    return (
                      <div key={claim.claim_id} className="p-3 bg-white border border-[#D9D4C7]/80 rounded-xl space-y-2 text-xs">
                        <div className="flex items-start justify-between gap-2">
                          <p className="font-medium text-[#0C0C12] leading-relaxed flex-1">
                            &ldquo;{claim.claim_text.slice(0, 120)}{claim.claim_text.length > 120 ? '...' : ''}&rdquo;
                          </p>
                          <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold shrink-0 ${pillColor}`}>
                            {claim.unmatched_entities?.length ? 'Entity Mismatch' : claim.status}
                          </span>
                        </div>

                        {/* Entity mismatch banner */}
                        {claim.unmatched_entities && claim.unmatched_entities.length > 0 && (
                          <div className="p-2 bg-[#FEF2F2] border border-[#FECACA] rounded-lg text-[10px] text-[#991B1B]">
                            Unmatched: {claim.unmatched_entities.map(e => `"${e}"`).join(', ')}
                          </div>
                        )}

                        {/* NLI logits */}
                        {claim.nli_logits && (
                          <div className="grid grid-cols-3 gap-1 pt-1.5 border-t border-[#F1EFEA] text-[10px] text-[#9A9890] font-mono tabular-nums">
                            <div>E: {(claim.nli_logits.entailment * 100).toFixed(1)}%</div>
                            <div>N: {(claim.nli_logits.neutral * 100).toFixed(1)}%</div>
                            <div>C: {(claim.nli_logits.contradiction * 100).toFixed(1)}%</div>
                          </div>
                        )}

                        {/* Evidence span */}
                        {claim.evidence_span && (
                          <div className="p-2 bg-[#FAF8F3] rounded-lg text-[10px] text-[#4A4842] border border-[#E5E1D8]">
                            <span className="font-semibold text-[#0C0C12]">Proof: </span>
                            <span className="italic font-serif">&ldquo;{claim.evidence_span.slice(0, 160)}&rdquo;</span>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>

                {/* Full dashboard link */}
                <a
                  href={`${apiBase || window.location.origin}?trace=${verification.request_id}`}
                  target="_blank"
                  rel="noreferrer"
                  className="block w-full py-2.5 px-3 bg-[#FAF8F3] hover:bg-[#F0EDE6] border border-[#D9D4C7] rounded-xl text-xs font-medium text-[#0C0C12] transition-colors text-center"
                >
                  View Full Audit Record in Dashboard
                </a>
              </>
            )}
          </div>
        </>
      )}
    </aside>
  );
}
