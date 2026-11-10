import type { ClaimRecord } from '../types';

interface EvidenceCardProps {
  claim: ClaimRecord;
}

export const EvidenceCard = ({ claim }: EvidenceCardProps) => {
  const isSupported = claim.status === 'Supported';
  const isContradicted = claim.status.toLowerCase().includes('contradict');
  const hasEntityMismatch = 
    claim.status.toLowerCase().includes('entity') || 
    Boolean(claim.unmatched_entities && claim.unmatched_entities.length > 0 && !isSupported);
  
  let badgeBg = 'bg-[#FEF3C7] text-[#92400E] border-[#FDE68A]';
  let label = 'Ungrounded';

  if (hasEntityMismatch) {
    badgeBg = 'bg-[#FEE2E2] text-[#991B1B] border-[#FECACA]';
    label = 'Entity Mismatch';
  } else if (isSupported) {
    badgeBg = 'bg-[#E8F8D6] text-[#2F6B12] border-[#C8EAA8]';
    label = 'Supported';
  } else if (isContradicted) {
    badgeBg = 'bg-[#FEE2E2] text-[#991B1B] border-[#FECACA]';
    label = 'Contradicted';
  }

  const normalize01 = (v: number | undefined | null): number => {
    if (v == null || isNaN(Number(v))) return 0;
    const n = Number(v);
    return n > 1.0 ? Math.min(1.0, n / 100) : Math.max(0, n);
  };

  const confidenceNorm = normalize01(claim.confidence);
  const confidencePct = (confidenceNorm * 100).toFixed(1);

  // Extract NLI logits with defensive 0.0 - 1.0 normalization
  const rawEntailment = claim.nli_logits 
    ? claim.nli_logits.entailment 
    : isSupported ? claim.confidence : (1 - claim.confidence) * 0.3;
  const entailmentVal = normalize01(rawEntailment);
    
  const rawContradiction = claim.nli_logits 
    ? claim.nli_logits.contradiction 
    : isContradicted ? claim.confidence : (1 - claim.confidence) * 0.3;
  const contradictionVal = normalize01(rawContradiction);
    
  const rawNeutral = claim.nli_logits 
    ? claim.nli_logits.neutral 
    : (!isSupported && !isContradicted) ? claim.confidence : 0.05;
  const neutralVal = normalize01(rawNeutral);

  return (
    <article className="rx-card p-5 md:p-6 mb-4 transition-shadow hover:shadow-md">
      <header className="flex flex-wrap items-center justify-between gap-3 pb-3 mb-3 border-b border-[#F2EFE8]">
        <div className="flex items-center gap-2.5">
          <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold border ${badgeBg}`}>
            {label}
          </span>
          <span className="text-xs text-[#7A7870] font-mono">
            claim #{claim.claim_id + 1}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-[#7A7870]">Confidence</span>
          <span className="font-serif text-base font-semibold text-[#0C0C12]">
            {confidencePct}%
          </span>
        </div>
      </header>

      {/* Claim Body */}
      <div className="mb-4">
        <p className="text-sm font-medium text-[#0C0C12] leading-relaxed">
          "{claim.claim_text || claim.text}"
        </p>
      </div>

      {/* Entity Violation Banner if present */}
      {claim.unmatched_entities && claim.unmatched_entities.length > 0 && (
        <div className="flex items-start gap-2.5 mb-4 p-3 rounded-xl bg-[#FEF2F2] border border-[#FECACA] text-xs text-[#991B1B]">
          <svg className="w-4 h-4 shrink-0 text-[#DC2626] mt-0.5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
            <path d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          <div className="leading-relaxed">
            <span className="font-semibold">Entity Grounding Violation:</span> Unmatched named entity{' '}
            {claim.unmatched_entities.map((ent, idx) => (
              <span key={idx} className="inline-block bg-white/90 border border-[#FECACA] font-mono text-[11px] font-semibold px-1.5 py-0.5 rounded mx-1 text-[#991B1B]">
                "{ent}"
              </span>
            ))}{' '}
            has no grounding antecedent in source evidence.
          </div>
        </div>
      )}

      {/* 3-Class NLI Softmax Micro-meters */}
      <div className="bg-[#FAF8F3] rounded-2xl p-3.5 border border-[#EBE7DC] mb-4">
        <div className="flex items-center justify-between mb-2">
          <span className="text-[11px] font-medium text-[#7A7870] uppercase tracking-wider">
            DeBERTa-v3 NLI Distribution
          </span>
          <span className="text-[11px] text-[#8C887E]">
            Softmax Probabilities
          </span>
        </div>
        <div className="grid grid-cols-3 gap-3">
          <div>
            <div className="flex justify-between text-xs mb-1">
              <span className="text-[#15803D] font-medium">Entailment</span>
              <span className="font-mono text-[#15803D] tabular-nums">{(entailmentVal * 100).toFixed(1)}%</span>
            </div>
            <div className="h-1.5 w-full bg-[#E8E4DA] rounded-full overflow-hidden">
              <div 
                className="h-full bg-[#15803D] rounded-full transition-[width] duration-300 ease-out"
                style={{ width: `${Math.min(100, entailmentVal * 100)}%` }}
              />
            </div>
          </div>

          <div>
            <div className="flex justify-between text-xs mb-1">
              <span className="text-[#DC2626] font-medium">Contradiction</span>
              <span className="font-mono text-[#DC2626] tabular-nums">{(contradictionVal * 100).toFixed(1)}%</span>
            </div>
            <div className="h-1.5 w-full bg-[#E8E4DA] rounded-full overflow-hidden">
              <div 
                className="h-full bg-[#DC2626] rounded-full transition-[width] duration-300 ease-out"
                style={{ width: `${Math.min(100, contradictionVal * 100)}%` }}
              />
            </div>
          </div>

          <div>
            <div className="flex justify-between text-xs mb-1">
              <span className="text-[#7A7870] font-medium">Neutral</span>
              <span className="font-mono text-[#7A7870] tabular-nums">{(neutralVal * 100).toFixed(1)}%</span>
            </div>
            <div className="h-1.5 w-full bg-[#E8E4DA] rounded-full overflow-hidden">
              <div 
                className="h-full bg-[#7A7870] rounded-full transition-[width] duration-300 ease-out"
                style={{ width: `${Math.min(100, neutralVal * 100)}%` }}
              />
            </div>
          </div>
        </div>
      </div>

      {/* Citation Evidence */}
      {(claim.evidence_span || claim.evidence) && (
        <div className="rounded-xl bg-[#F5F2EB]/80 p-3 border border-[#E5E1D8] text-xs">
          <div className="flex items-center gap-1.5 text-[#5F5D56] font-medium mb-1.5">
            <svg className="w-3.5 h-3.5 text-[#7A7870]" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
              <path d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            <span>Reference Ground Truth Citation</span>
          </div>
          <p className="text-[#383631] italic font-serif leading-relaxed">
            "{claim.evidence_span || claim.evidence}"
          </p>
        </div>
      )}
    </article>
  );
};
