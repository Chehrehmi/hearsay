import { useState } from 'react';
import type { VerificationResult } from '../types';
import { EvidenceCard } from './EvidenceCard';
import { formatPercentage } from '../utils/formatters';

interface SandboxViewProps {
  onVerificationSuccess?: (result: VerificationResult) => void;
}

export const SandboxView = ({ onVerificationSuccess }: SandboxViewProps) => {
  const [sourceId, setSourceId] = useState('doc_hist_india');
  const [sourceContext, setSourceContext] = useState(
    'India achieved independence from British rule on August 15, 1947, following the passage of the Indian Independence Act.'
  );
  const [responseText, setResponseText] = useState(
    'India achieved its independence on August 15, 1950, ending decades of colonial governance.'
  );
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<VerificationResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const presets = [
    {
      label: 'Date Conflict (India 1947)',
      sourceId: 'doc_hist_india',
      context: 'India achieved independence from British rule on August 15, 1947, following the passage of the Indian Independence Act.',
      response: 'India achieved its independence on August 15, 1950, ending decades of colonial governance.'
    },
    {
      label: 'Factual Fabrication (Apollo 11)',
      sourceId: 'doc_space_apollo',
      context: 'The Apollo 11 mission was launched on July 16, 1969, and landed the first humans on the Moon on July 20, 1969.',
      response: 'The Apollo 11 mission successfully landed astronauts on Mars in July 1969.'
    },
    {
      label: 'RAGTruth Benchmark (Anne Frank)',
      sourceId: 'doc_ragtruth_annefrank',
      context: 'Witnesses suggest that Anne and Margot Frank showed severe symptoms before February 7, 1945, in the Bergen-Belsen camp.',
      response: 'Anne Frank contracted typhus in the Bergen-Belsen camp and died before February 7, 2022.'
    },
    {
      label: 'Grounded Reference (Clean)',
      sourceId: 'doc_hist_valid',
      context: 'The Indian Independence Act was enacted by the Parliament of the United Kingdom in 1947.',
      response: 'The Indian Independence Act was enacted by the British Parliament in 1947.'
    },
    {
      label: 'ALCE Citation Binding (ASQA EMNLP 2023)',
      sourceId: 'alce_asqa_football',
      context: '[Doc 1] Pele scored 1281 goals according to IFFHS records.\n[Doc 2] Josef Bican scored at least 805 goals in all competitive matches.\n[Doc 3] Godfrey Chitalu was claimed by the Football Association of Zambia to have scored 116 goals in 1972.',
      response: 'Josef Bican scored at least 805 goals in competitive matches [Doc 2]. Godfrey Chitalu scored 116 goals in 1972 [Doc 3]. Pele scored 5000 goals in World Cup tournaments [Doc 1].'
    }
  ];

  const handleRunVerification = async () => {
    if (!sourceContext.trim() || !responseText.trim()) {
      setError('Please provide both context and candidate response text.');
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const apiBase = window.location.port === '5173' ? 'http://localhost:8000' : '';
      const payload = {
        response_text: responseText.trim(),
        response: responseText.trim(),
        verirag_context: {
          source_id: sourceId.trim() || 'doc_user_input',
          source_info: sourceContext.trim()
        },
        context: {
          source_id: sourceId.trim() || 'doc_user_input',
          source_info: sourceContext.trim()
        }
      };

      const res = await fetch(`${apiBase}/verify`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload)
      });

      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        throw new Error(errorData.detail || `Gateway error (HTTP ${res.status})`);
      }

      const data: VerificationResult = await res.json();
      setResult(data);
      if (onVerificationSuccess) {
        onVerificationSuccess(data);
      }
    } catch (err: any) {
      console.error('Verification failed:', err);
      setError(err.message || 'Failed to communicate with the verification gateway.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSelectPreset = (preset: typeof presets[0]) => {
    setSourceId(preset.sourceId);
    setSourceContext(preset.context);
    setResponseText(preset.response);
    setResult(null);
    setError(null);
  };

  return (
    <div className="space-y-6">
      {/* Architecture Profile & Scenario Header */}
      <section className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <article className="lg:col-span-5 rx-card p-6 md:p-7 flex flex-col justify-between shadow-card border border-black/5 bg-white">
          <div>
            <div className="flex items-center gap-2">
              <span className="inline-flex items-center gap-1.5 bg-[#FAF8F3] text-[#0C0C12] border border-[#E5E1D8] px-3 py-1 rounded-full text-[11px] font-medium tracking-wide shadow-xs">
                <span className="w-2 h-2 rounded-full bg-[#15803D]" />
                <span>Zero-Shot NLI · Cross-Encoder</span>
              </span>
            </div>

            <div className="pt-6">
              <h2 className="font-serif text-2xl md:text-3xl font-semibold text-[#0C0C12] leading-[1.2] tracking-tight">
                Runtime Groundedness <br />
                <span className="italic font-normal">Verification Workbench</span>
              </h2>
              <p className="text-xs md:text-sm text-[#7A7870] font-normal mt-2.5 leading-relaxed">
                Direct cross-examination of generative model outputs against retrieved context premises with sentence-level claim decomposition and contradiction detection.
              </p>
            </div>
          </div>

          <div className="pt-4 mt-4 border-t border-[#F2EFE8] flex items-center justify-between text-[11px] text-[#7A7870] font-mono">
            <span>Threshold: P(Contradiction) &gt; 0.50</span>
            <span className="text-[#15803D] font-medium">Local CPU Intercept</span>
          </div>
        </article>

        {/* Quick Scenario Preset Chips */}
        <article className="lg:col-span-7 rx-card p-7 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-4 border-b border-[#F2EFE8]">
              <div>
                <h3 className="font-serif text-lg font-semibold text-[#0C0C12]">Benchmark Presets</h3>
                <p className="text-xs text-[#7A7870] mt-0.5">Select a preconfigured scenario to test contradiction catching</p>
              </div>
              <span className="text-xs text-[#7A7870] font-mono">{presets.length} Scenarios</span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 mt-4">
              {presets.map((preset, idx) => (
                <button
                  key={idx}
                  onClick={() => handleSelectPreset(preset)}
                  className="flex items-center justify-between p-3 rounded-2xl bg-[#FAF8F3] hover:bg-[#F2EEE4] border border-[#EBE7DC] text-left transition-colors group"
                >
                  <div className="overflow-hidden">
                    <div className="text-xs font-semibold text-[#0C0C12] group-hover:text-black">
                      {preset.label}
                    </div>
                    <div className="text-[11px] text-[#7A7870] truncate mt-0.5">
                      {preset.sourceId}
                    </div>
                  </div>
                  <svg className="w-4 h-4 text-[#8C887E] group-hover:text-[#0C0C12] transition-colors shrink-0 ml-2" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                    <path d="M9 5l7 7-7 7" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </button>
              ))}
            </div>
          </div>

          <div className="pt-4 mt-4 border-t border-[#F2EFE8] flex items-center justify-between text-xs text-[#7A7870]">
            <span>Model: DeBERTa-v3-small (Local CPU)</span>
            <span>Task: Sentence-level NLI entailment</span>
          </div>
        </article>
      </section>

      {/* Editor Split Grid */}
      <section className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Source Document Context */}
        <article className="rx-card p-6 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-4 border-b border-[#F2EFE8]">
              <div className="flex items-center gap-2">
                <div className="w-7 h-7 rounded-lg bg-[#FAF7F2] flex items-center justify-center text-[#0C0C12] shrink-0" style={{ width: '28px', height: '28px' }}>
                  <svg className="w-4 h-4" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                    <path d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </div>
                <h3 className="font-serif text-base font-semibold text-[#0C0C12]">
                  Reference Context Document
                </h3>
              </div>
              <input
                type="text"
                value={sourceId}
                onChange={(e) => setSourceId(e.target.value)}
                placeholder="doc_id"
                className="text-xs font-mono bg-[#FAF8F3] border border-[#E5E1D8] px-2.5 py-1 rounded-lg text-[#0C0C12] focus:outline-none focus:ring-1 focus:ring-[#0C0C12]/20 focus:border-[#0C0C12]"
              />
            </div>

            <div className="mt-4">
              <textarea
                rows={7}
                value={sourceContext}
                onChange={(e) => setSourceContext(e.target.value)}
                placeholder="Paste retrieved source evidence chunk..."
                className="w-full p-3.5 bg-[#FAF8F3] rounded-2xl border border-[#E5E1D8] text-sm text-[#0C0C12] leading-relaxed resize-none focus:outline-none focus:ring-2 focus:ring-[#0C0C12]/15 focus:border-[#0C0C12] transition-colors"
              />
            </div>
          </div>

          <div className="pt-3 mt-2 flex justify-between items-center text-xs text-[#7A7870]">
            <span>{sourceContext.length} characters</span>
            <span>Ground truth baseline</span>
          </div>
        </article>

        {/* Candidate LLM Response */}
        <article className="rx-card p-6 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-4 border-b border-[#F2EFE8]">
              <div className="flex items-center gap-2">
                <div className="w-7 h-7 rounded-lg bg-[#FAF7F2] flex items-center justify-center text-[#0C0C12] shrink-0" style={{ width: '28px', height: '28px' }}>
                  <svg className="w-4 h-4" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                    <rect height="14" rx="2" width="20" x="2" y="3" />
                    <line x1="8" x2="16" y1="21" y2="21" />
                    <line x1="12" x2="12" y1="17" y2="21" />
                  </svg>
                </div>
                <h3 className="font-serif text-base font-semibold text-[#0C0C12]">
                  Candidate Response Output
                </h3>
              </div>
              <span className="text-xs text-[#7A7870]">Target for audit</span>
            </div>

            <div className="mt-4">
              <textarea
                rows={7}
                value={responseText}
                onChange={(e) => setResponseText(e.target.value)}
                placeholder="Enter model generation to verify..."
                className="w-full p-3.5 bg-[#FAF8F3] rounded-2xl border border-[#E5E1D8] text-sm text-[#0C0C12] leading-relaxed resize-none focus:outline-none focus:ring-2 focus:ring-[#0C0C12]/15 focus:border-[#0C0C12] transition-colors"
              />
            </div>
          </div>

          <div className="pt-3 mt-2 flex justify-between items-center text-xs text-[#7A7870]">
            <span>{responseText.length} characters</span>
            <span>Split into atomic claims</span>
          </div>
        </article>
      </section>

      {/* Floating Action Bar */}
      <section className="rx-card p-4 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <button
            onClick={() => {
              setSourceContext('');
              setResponseText('');
              setResult(null);
              setError(null);
            }}
            className="px-4 py-2 rounded-full border border-[#D9D4C7] bg-white text-xs font-medium text-[#47453F] hover:bg-[#F6F5F1] transition-colors"
          >
            Clear Fields
          </button>
          {error && (
            <span className="text-xs text-[#DC2626] font-medium">
              {error}
            </span>
          )}
        </div>

        <button
          onClick={handleRunVerification}
          disabled={isLoading}
          className="flex items-center gap-2 bg-[#0C0C12] hover:bg-black text-white text-xs md:text-sm font-medium px-5 py-2.5 rounded-full shadow-sm transition-transform active:scale-95 disabled:opacity-50"
        >
          {isLoading ? (
            <>
              <svg className="animate-spin w-4 h-4 text-white" width="16" height="16" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
              </svg>
              <span>Verifying Claims...</span>
            </>
          ) : (
            <>
              <span>Execute Groundedness Scan</span>
              <svg className="w-4 h-4" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2.2" viewBox="0 0 24 24">
                <path d="M14 5l7 7m0 0l-7 7m7-7H3" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </>
          )}
        </button>
      </section>

      {/* Verification Result Showcase */}
      {result && (
        <section className="space-y-4">
          {/* Verdict Banner */}
          <article className="rx-card p-6 border border-black/5">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-[#F2EFE8]">
              <div>
                {(() => {
                  const isGrounded = result.grounded ?? (result.overall_status === 'Verified');
                  return (
                    <>
                      <div className="flex items-center gap-2">
                        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold ${
                          isGrounded
                            ? 'bg-[#E8F8D6] text-[#2F6B12]'
                            : 'bg-[#FEE2E2] text-[#991B1B]'
                        }`}>
                          {isGrounded ? 'Grounded & Verified' : 'Hallucination Detected'}
                        </span>
                        <span className="text-xs text-[#7A7870]">
                          Request ID: {result.request_id || 'req_live_session'}
                        </span>
                      </div>
                      <h2 className="font-serif text-2xl font-semibold text-[#0C0C12] mt-2">
                        {isGrounded
                          ? 'All extracted claims are factual and supported by source evidence.'
                          : 'Candidate response contains contradicted or ungrounded assertions.'}
                      </h2>
                    </>
                  );
                })()}
              </div>

              <div className="flex items-baseline gap-4 sm:border-l sm:border-[#F2EFE8] sm:pl-6">
                <div>
                  <div className="text-xs text-[#7A7870]">Groundedness Score</div>
                  <div className="font-serif text-3xl font-semibold text-[#0C0C12]">
                    {formatPercentage(result.groundedness_score)}
                  </div>
                </div>
                <div>
                  <div className="text-xs text-[#7A7870]">Claims Evaluated</div>
                  <div className="font-serif text-3xl font-semibold text-[#0C0C12]">
                    {result.claims.length}
                  </div>
                </div>
              </div>
            </div>

            {/* Extracted Claims Evidence List */}
            <div className="mt-6">
              <h3 className="font-serif text-lg font-semibold text-[#0C0C12] mb-3">
                Extracted Claims & Evidence Attribution
              </h3>
              <div className="space-y-3">
                {result.claims.map((claim) => (
                  <EvidenceCard key={claim.claim_id} claim={claim} />
                ))}
              </div>
            </div>
          </article>
        </section>
      )}
    </div>
  );
};
