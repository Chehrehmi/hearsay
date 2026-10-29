import { useState, useEffect } from 'react';
import type { TraceRecord } from '../types';
import { EvidenceCard } from './EvidenceCard';
import { formatPercentage } from '../utils/formatters';

interface TraceExplorerViewProps {
  initialSearch?: string;
}

export const TraceExplorerView = ({ initialSearch = '' }: TraceExplorerViewProps) => {
  const [traces, setTraces] = useState<TraceRecord[]>([]);
  const [statusFilter, setStatusFilter] = useState<string>('All');
  const [searchQuery, setSearchQuery] = useState<string>(initialSearch);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [selectedTrace, setSelectedTrace] = useState<TraceRecord | null>(null);

  useEffect(() => {
    if (initialSearch !== undefined) {
      setSearchQuery(initialSearch);
    }
  }, [initialSearch]);

  const fetchTraces = async () => {
    setIsLoading(true);
    try {
      const apiBase = window.location.port === '5173' ? 'http://localhost:8000' : '';
      const res = await fetch(`${apiBase}/v1/traces?limit=50`);
      if (res.ok) {
        const data = await res.json();
        const parsed = (data || []).map((t: any) => ({
          ...t,
          claims: typeof t.claims === 'string' ? JSON.parse(t.claims) : t.claims
        }));
        setTraces(parsed);
      }
    } catch (err) {
      console.error('Failed to fetch verification traces:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchTraces();
  }, []);

  const filteredTraces = traces.filter((trace) => {
    const isGrounded = trace.grounded ?? (trace.overall_status === 'Verified');
    const matchesFilter =
      statusFilter === 'All'
        ? true
        : statusFilter === 'Supported'
        ? isGrounded === true
        : isGrounded === false;

    const matchesSearch =
      (trace.request_id || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
      (trace.response_text || '').toLowerCase().includes(searchQuery.toLowerCase());

    return matchesFilter && matchesSearch;
  });

  return (
    <div className="space-y-6">
      {/* Title & Control Row */}
      <section className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="font-serif text-3xl font-semibold text-[#0C0C12] tracking-tight">
            Runtime Audit Traces
          </h1>
          <p className="text-xs md:text-sm text-[#7A7870] mt-1">
            Persisted SQLite verification logs for compliance, claim attribution, and latency audits
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            onClick={fetchTraces}
            disabled={isLoading}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 bg-white rounded-full border border-black/5 shadow-pill text-xs font-medium text-[#0C0C12] hover:bg-[#F6F5F1] transition-colors"
          >
            <svg className={`w-3.5 h-3.5 text-[#5F5D56] ${isLoading ? 'animate-spin' : ''}`} width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
              <path d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            <span>Refresh</span>
          </button>
        </div>
      </section>

      {/* High-Density Audit Table Card */}
      <article className="rx-card p-6 md:p-7 shadow-card border border-black/5 flex flex-col justify-between">
        <div>
          {/* Table Header Controls */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-5 border-b border-[#F2EFE8]">
            {/* Filter Pills */}
            <div className="flex items-center gap-2">
              <span className="text-xs font-medium text-[#7A7870] mr-1">Filter:</span>
              {(['All', 'Supported', 'Contradictions'] as const).map((mode) => (
                <button
                  key={mode}
                  onClick={() => setStatusFilter(mode)}
                  className={`px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
                    statusFilter === mode
                      ? 'bg-[#0C0C12] text-white shadow-sm'
                      : 'bg-[#F6F5F1] text-[#5F5D56] hover:bg-[#ECE9E0]'
                  }`}
                >
                  {mode}
                </button>
              ))}
            </div>

            {/* Search Input */}
            <div className="relative">
              <svg className="w-3.5 h-3.5 text-[#7A7870] absolute left-3 top-2.5 pointer-events-none" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                <path d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search trace or text..."
                className="pl-8 pr-4 py-1.5 bg-[#FAF8F3] border border-[#E5E1D8] rounded-full text-xs text-[#0C0C12] placeholder-[#8C887E] focus:outline-none focus:border-[#BD47F2] transition-colors"
              />
            </div>
          </div>

          {/* Table Element */}
          <div className="overflow-x-auto mt-2">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="text-[11px] font-medium text-[#8C887E] uppercase tracking-wider border-b border-[#F7F5F0]">
                  <th className="py-3 px-3">Trace ID</th>
                  <th className="py-3 px-3">Generated Response</th>
                  <th className="py-3 px-3">Status</th>
                  <th className="py-3 px-3">Latency</th>
                  <th className="py-3 px-3 text-right">Groundedness</th>
                  <th className="py-3 px-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#F9F7F2] text-xs">
                {filteredTraces.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="py-8 text-center text-[#7A7870]">
                      No verification traces found. Run a scan from the Playground to generate live traces.
                    </td>
                  </tr>
                ) : (
                  filteredTraces.map((trace) => {
                    const isGrounded = trace.grounded ?? (trace.overall_status === 'Verified');
                    return (
                      <tr key={trace.request_id} className="hover:bg-[#FAF9F5] transition-colors">
                        <td className="py-3.5 px-3 font-mono text-[11px] text-[#0C0C12]">
                          {trace.request_id.slice(0, 16)}...
                        </td>
                        <td className="py-3.5 px-3 max-w-xs md:max-w-md truncate text-[#4A4841]">
                          "{trace.response_text}"
                        </td>
                        <td className="py-3.5 px-3">
                          <span
                            className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-medium ${
                              isGrounded
                                ? 'bg-[#E8F8D6] text-[#2F6B12]'
                                : 'bg-[#FEE2E2] text-[#991B1B]'
                            }`}
                          >
                            {isGrounded ? 'Grounded' : 'Contradiction'}
                          </span>
                        </td>
                        <td className="py-3.5 px-3 font-mono text-[#7A7870]">
                          {trace.latency_ms ? `${trace.latency_ms.toFixed(0)} ms` : '—'}
                        </td>
                        <td className="py-3.5 px-3 text-right font-serif text-sm font-semibold text-[#0C0C12]">
                          {formatPercentage(trace.groundedness_score)}
                        </td>
                        <td className="py-3.5 px-3 text-right">
                          <button
                            onClick={() => setSelectedTrace(trace)}
                            className="inline-flex items-center gap-1 px-3 py-1 bg-[#F6F5F1] hover:bg-[#ECE9E0] text-[#0C0C12] text-xs font-medium rounded-full transition-colors"
                          >
                            <span>Inspect</span>
                            <svg className="w-3 h-3 text-[#5F5D56]" width="12" height="12" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                              <path d="M9 5l7 7-7 7" strokeLinecap="round" strokeLinejoin="round" />
                            </svg>
                          </button>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Table Footer */}
        <div className="pt-4 mt-2 border-t border-[#F2EFE8] flex items-center justify-between text-[11px] text-[#8C887E]">
          <span>Showing {filteredTraces.length} recorded verification events</span>
          <span>SQLite Store: hearsay_traces.db</span>
        </div>
      </article>

      {/* Slide-In Inspector Drawer */}
      {selectedTrace && (
        <div className="fixed inset-0 z-50 flex justify-end bg-black/30 backdrop-blur-xs">
          <div className="w-full max-w-xl bg-white h-full shadow-2xl p-6 md:p-8 overflow-y-auto flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between pb-4 border-b border-[#F2EFE8]">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono text-[#7A7870]">
                      {selectedTrace.request_id}
                    </span>
                    <span
                      className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold ${
                        (selectedTrace.grounded ?? (selectedTrace.overall_status === 'Verified'))
                          ? 'bg-[#E8F8D6] text-[#2F6B12]'
                          : 'bg-[#FEE2E2] text-[#991B1B]'
                      }`}
                    >
                      {(selectedTrace.grounded ?? (selectedTrace.overall_status === 'Verified')) ? 'Grounded' : 'Contradiction'}
                    </span>
                  </div>
                  <h2 className="font-serif text-2xl font-semibold text-[#0C0C12] mt-1.5">
                    Trace Inspection Details
                  </h2>
                </div>
                <button
                  onClick={() => setSelectedTrace(null)}
                  className="w-8 h-8 rounded-full bg-[#FAF8F3] hover:bg-[#EBE7DC] flex items-center justify-center text-[#5F5D56] transition-colors"
                  aria-label="Close inspector"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                    <path d="M6 18L18 6M6 6l12 12" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </button>
              </div>

              {/* Payload Summary */}
              <div className="my-5 space-y-4">
                <div className="rounded-2xl bg-[#FAF8F3] p-4 border border-[#EBE7DC]">
                  <div className="text-xs font-medium text-[#7A7870] mb-1">
                    Candidate Response Output
                  </div>
                  <p className="text-sm text-[#0C0C12] leading-relaxed">
                    "{selectedTrace.response_text}"
                  </p>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div className="rounded-2xl bg-[#FAF8F3] p-3.5 border border-[#EBE7DC]">
                    <div className="text-xs text-[#7A7870]">Groundedness Score</div>
                    <div className="font-serif text-2xl font-semibold text-[#0C0C12] mt-0.5">
                      {formatPercentage(selectedTrace.groundedness_score)}
                    </div>
                  </div>
                  <div className="rounded-2xl bg-[#FAF8F3] p-3.5 border border-[#EBE7DC]">
                    <div className="text-xs text-[#7A7870]">Execution Latency</div>
                    <div className="font-serif text-2xl font-semibold text-[#0C0C12] mt-0.5">
                      {selectedTrace.latency_ms ? `${selectedTrace.latency_ms.toFixed(0)} ms` : '—'}
                    </div>
                  </div>
                </div>

                {/* Claims Evaluated */}
                <div className="pt-4 border-t border-[#F2EFE8]">
                  <h3 className="font-serif text-base font-semibold text-[#0C0C12] mb-3">
                    Claims & Evidence Attribution
                  </h3>
                  <div className="space-y-3">
                    {Array.isArray(selectedTrace.claims) && selectedTrace.claims.length > 0 ? (
                      selectedTrace.claims.map((claim: any) => (
                        <EvidenceCard key={claim.claim_id} claim={claim} />
                      ))
                    ) : (
                      <p className="text-xs text-[#7A7870]">No individual claims parsed in this trace.</p>
                    )}
                  </div>
                </div>
              </div>
            </div>

            <div className="pt-4 border-t border-[#F2EFE8] flex justify-end">
              <button
                onClick={() => setSelectedTrace(null)}
                className="px-5 py-2 rounded-full bg-[#0C0C12] text-white text-xs font-medium hover:bg-black transition-colors"
              >
                Close Inspector
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
