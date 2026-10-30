import { useState, useEffect } from 'react';
import type { MetricSummary, TraceRecord } from '../types';
import { formatPercentage } from '../utils/formatters';

interface AnalyticsViewProps {
  metrics: MetricSummary | null;
}

export const AnalyticsView: React.FC<AnalyticsViewProps> = ({ metrics }) => {
  const [traces, setTraces] = useState<TraceRecord[]>([]);
  const [hoveredTrace, setHoveredTrace] = useState<TraceRecord | null>(null);

  useEffect(() => {
    const apiBase = window.location.port === '5173' ? 'http://localhost:8000' : '';
    fetch(`${apiBase}/v1/traces?limit=14`)
      .then((res) => (res.ok ? res.json() : []))
      .then((data) => {
        if (Array.isArray(data)) {
          // Reverse so chronological order goes left to right
          setTraces([...data].reverse());
        }
      })
      .catch((err) => console.error('Failed to load telemetry traces:', err));
  }, []);

  const totalClaims = metrics?.total_claims ?? 0;
  const supportedClaims = metrics?.total_supported ?? 0;
  const contradictedClaims = metrics?.total_contradicted ?? 0;
  const ungroundedClaims = metrics?.total_ungrounded ?? 0;

  const suppPct = totalClaims > 0 ? Math.round((supportedClaims / totalClaims) * 100) : 0;
  const contPct = totalClaims > 0 ? Math.round((contradictedClaims / totalClaims) * 100) : 0;
  const ungrPct = totalClaims > 0 ? Math.round((ungroundedClaims / totalClaims) * 100) : 0;

  const p50 = metrics?.p50_latency_ms ?? 0;
  const p95 = metrics?.p95_latency_ms ?? 0;
  const avg = metrics?.avg_latency_ms ?? 0;
  const passRate = metrics?.verification_pass_rate ?? 0;

  // Compute robust scale for latency chart (ignore cold-start spikes > 15s for visual scaling)
  const validLatencies = traces.map((t) => t.latency_ms || 0);
  const normalLatencies = validLatencies.filter((l) => l < 15000);
  const maxNormal = normalLatencies.length > 0 ? Math.max(...normalLatencies) : 2500;
  const chartMax = Math.max(1500, Math.ceil(maxNormal / 500) * 500);

  const activePills = Math.min(20, Math.max(0, Math.round((passRate / 100) * 20)));

  return (
    <div className="space-y-6">
      {/* Title Row */}
      <section className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="font-serif text-3xl font-semibold text-[#0C0C12] tracking-tight">
            System Observability & Reliability
          </h1>
          <p className="text-xs md:text-sm text-[#7A7870] mt-1">
            Real-time latency distributions and factual verification telemetry across recent requests
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-white rounded-full border border-black/5 shadow-pill text-xs font-medium text-[#0C0C12]">
            <span className="w-2 h-2 rounded-full bg-[#15803D]" />
            <span>SQLite Audit Store: Active</span>
          </span>
        </div>
      </section>

      {/* Top Grid: Real Telemetry Latency Distribution & Pass Rate */}
      <section className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Main Chart Card: Real Verification Latency Distribution */}
        <article className="lg:col-span-8 rx-card p-6 md:p-7 shadow-card border border-black/5 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div
                  className="w-7 h-7 rounded-lg bg-[#FAF7F2] flex items-center justify-center text-[#0C0C12] shrink-0"
                  style={{ width: '28px', height: '28px' }}
                >
                  <svg className="w-4 h-4" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                    <path d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </div>
                <h3 className="font-serif text-lg font-semibold text-[#0C0C12]">
                  Verification Latency History
                </h3>
              </div>
              <div className="flex items-center gap-3">
                <div className="hidden sm:flex items-center gap-2.5 text-[11px] text-[#7A7870]">
                  <span className="flex items-center gap-1">
                    <span className="w-2.5 h-2.5 rounded-full bg-[#15803D]" />
                    <span>Grounded</span>
                  </span>
                  <span className="flex items-center gap-1">
                    <span className="w-2.5 h-2.5 rounded-full bg-[#DC2626]" />
                    <span>Hallucinated</span>
                  </span>
                </div>
                <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-[#F6F5F1] text-[#0C0C12] text-xs font-medium rounded-full font-mono">
                  <span>{traces.length} Recent Scans</span>
                </span>
              </div>
            </div>

            {/* Metric Banner with Real Data */}
            <div className="mt-4 flex flex-wrap items-baseline gap-3">
              <span className="font-serif text-3xl md:text-[34px] font-semibold tracking-tight text-[#0C0C12] font-mono tabular-nums">
                {metrics?.total_requests ?? 0} Total Requests
              </span>
              <span className="text-xs text-[#8C887E] font-mono tabular-nums">
                Avg Groundedness: {formatPercentage(metrics?.avg_groundedness_score)}
              </span>
              <span className="text-xs text-[#8C887E] font-mono tabular-nums">
                Mean Latency: {avg} ms
              </span>
            </div>

            {/* Dynamic Latency Histogram from Real Stored Traces */}
            <div className="mt-6 relative h-[210px] w-full flex flex-col justify-end bg-[#FAF8F3] rounded-2xl p-4 border border-[#EBE7DC]">
              {traces.length === 0 ? (
                <div className="h-full flex items-center justify-center text-xs text-[#8C887E]">
                  No verification scans recorded yet. Execute a scan in the Workbench to see real-time latency analytics.
                </div>
              ) : (
                <>
                  {/* Subtle Reference Gridlines */}
                  <div className="absolute inset-x-4 top-4 bottom-10 flex flex-col justify-between pointer-events-none opacity-40">
                    <div className="border-b border-dashed border-[#D9D4C7] w-full flex justify-end text-[9px] text-[#8C887E]">
                      <span>{chartMax} ms</span>
                    </div>
                    <div className="border-b border-dashed border-[#D9D4C7] w-full flex justify-end text-[9px] text-[#8C887E]">
                      <span>{Math.round(chartMax * 0.66)} ms</span>
                    </div>
                    <div className="border-b border-dashed border-[#D9D4C7] w-full flex justify-end text-[9px] text-[#8C887E]">
                      <span>{Math.round(chartMax * 0.33)} ms</span>
                    </div>
                  </div>

                  {/* Bars Container */}
                  <div className="relative z-10 h-[140px] w-full flex items-end justify-between gap-2 px-1 pb-1">
                    {traces.map((trace) => {
                      const lat = trace.latency_ms || 0;
                      // Height normalized to container
                      const pct = Math.max(12, Math.min(100, Math.round((lat / chartMax) * 100)));
                      const isGrounded = trace.grounded ?? (trace.overall_status === 'Verified');

                      return (
                        <div
                          key={trace.request_id}
                          className="flex-1 flex flex-col items-center h-full justify-end group relative cursor-pointer"
                          onMouseEnter={() => setHoveredTrace(trace)}
                          onMouseLeave={() => setHoveredTrace(null)}
                        >
                          <div
                            className={`w-full max-w-[28px] rounded-t-md transition-all duration-200 shadow-sm ${
                              isGrounded
                                ? 'bg-[#15803D] hover:bg-[#166534]'
                                : 'bg-[#DC2626] hover:bg-[#B91C1C]'
                            }`}
                            style={{ height: `${pct}%` }}
                          />
                        </div>
                      );
                    })}
                  </div>

                  {/* Active Tooltip */}
                  {hoveredTrace && (
                    <div className="absolute top-3 left-4 bg-white/95 backdrop-blur-xs px-3.5 py-2 rounded-xl border border-black/10 shadow-lg text-[11px] pointer-events-none z-20">
                      <div className="flex items-center gap-2 font-semibold text-[#0C0C12]">
                        <span className="font-mono text-xs">{hoveredTrace.request_id.slice(0, 12)}...</span>
                        <span className={`text-[9px] px-1.5 py-0.5 rounded font-bold ${
                          (hoveredTrace.grounded ?? (hoveredTrace.overall_status === 'Verified'))
                            ? 'bg-[#E8F8D6] text-[#15803D]'
                            : 'bg-[#FEE2E2] text-[#991B1B]'
                        }`}>
                          {(hoveredTrace.grounded ?? (hoveredTrace.overall_status === 'Verified')) ? 'Verified' : 'Contradiction'}
                        </span>
                      </div>
                      <div className="text-[10px] text-[#5F5D56] mt-1 flex gap-3 font-mono tabular-nums">
                        <span>Latency: <strong>{hoveredTrace.latency_ms?.toFixed(0)} ms</strong></span>
                        <span>
                          Groundedness: <strong>{formatPercentage(hoveredTrace.groundedness_score)}</strong>
                        </span>
                      </div>
                    </div>
                  )}

                  {/* Axis labels */}
                  <div className="pt-2 flex justify-between text-[11px] text-[#8C887E] font-medium px-1 border-t border-[#E8E4DA] font-mono">
                    <span>Oldest ({traces[0]?.request_id.slice(0, 8)}...)</span>
                    <span>Recent Scans (P50: {p50} ms)</span>
                    <span>Latest ({traces[traces.length - 1]?.request_id.slice(0, 8)}...)</span>
                  </div>
                </>
              )}
            </div>
          </div>
        </article>

        {/* Goal Progress Card: Real Verification Pass Rate */}
        <article className="lg:col-span-4 rx-card p-6 shadow-card border border-black/5 flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2">
              <div
                className="w-7 h-7 rounded-lg bg-[#FAF7F2] flex items-center justify-center text-[#0C0C12] shrink-0"
                style={{ width: '28px', height: '28px' }}
              >
                <svg className="w-4 h-4" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                  <path d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </div>
              <h3 className="font-serif text-base font-semibold text-[#0C0C12]">Verification Pass Rate</h3>
            </div>

            <div className="mt-4 flex items-baseline gap-2">
              <span className="font-serif text-4xl font-semibold text-[#0C0C12] tracking-tight font-mono tabular-nums">
                {passRate.toFixed(1)}%
              </span>
              <span className="text-xs text-[#7A7870]">factual integrity</span>
            </div>

            {/* 20 Segmented Micro-Pills */}
            <div className="mt-4 flex items-center gap-1 overflow-hidden">
              {Array.from({ length: 20 }).map((_, idx) => (
                <span
                  key={idx}
                  className={`h-5 w-1 rounded-full transition-colors ${
                    idx < activePills ? (passRate >= 80 ? 'bg-[#15803D]' : 'bg-[#D97706]') : 'bg-[#EAE7DF]'
                  }`}
                />
              ))}
            </div>
            <p className="text-[11px] text-[#7A7870] mt-2">
              {metrics?.total_verified ?? 0} verified clean out of {metrics?.total_requests ?? 0} total requests.
            </p>
          </div>

          <div className="mt-6 pt-4 border-t border-[#F5F2EB] flex items-center justify-between text-xs">
            <div>
              <div className="font-medium text-[#15803D] font-mono tabular-nums">
                {metrics?.total_verified ?? 0} Passed
              </div>
              <div className="text-[10px] text-[#7A7870]">Zero contradictions</div>
            </div>
            <div className="text-right">
              <div className="font-medium text-[#DC2626] font-mono tabular-nums">
                {metrics?.total_hallucinations ?? 0} Flagged
              </div>
              <div className="text-[10px] text-[#7A7870]">Hallucinations intercepted</div>
            </div>
          </div>
        </article>
      </section>

      {/* Latency Percentiles & Claim Breakdown */}
      <section className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Latency Percentiles */}
        <article className="rx-card p-6 md:p-7 shadow-card border border-black/5">
          <div className="flex items-center justify-between pb-4 border-b border-[#F2EFE8]">
            <h3 className="font-serif text-lg font-semibold text-[#0C0C12]">
              Inference Latency Percentiles
            </h3>
            <span className="text-xs text-[#7A7870] font-mono">PyTorch/CPU</span>
          </div>

          <div className="grid grid-cols-3 gap-3 my-5">
            <div className="rounded-2xl bg-[#FAF8F3] p-4 border border-[#EBE7DC]">
              <div className="text-xs text-[#7A7870]">P50 Median</div>
              <div className="font-serif text-2xl font-semibold text-[#0C0C12] mt-1 font-mono tabular-nums">{p50} ms</div>
              <div className="text-[10px] text-[#15803D] mt-0.5">Median scan</div>
            </div>

            <div className="rounded-2xl bg-[#FAF8F3] p-4 border border-[#EBE7DC]">
              <div className="text-xs text-[#7A7870]">Mean Latency</div>
              <div className="font-serif text-2xl font-semibold text-[#0C0C12] mt-1 font-mono tabular-nums">{avg} ms</div>
              <div className="text-[10px] text-[#7A7870] mt-0.5">Across all scans</div>
            </div>

            <div className="rounded-2xl bg-[#FAF8F3] p-4 border border-[#EBE7DC]">
              <div className="text-xs text-[#7A7870]">P95 Tail</div>
              <div className="font-serif text-2xl font-semibold text-[#DC2626] mt-1 font-mono tabular-nums">{p95} ms</div>
              <div className="text-[10px] text-[#DC2626] mt-0.5">Tail bound</div>
            </div>
          </div>

          <div className="pt-3 border-t border-[#F2EFE8] text-xs text-[#7A7870]">
            Zero-shot cross-encoder evaluates sentence-level NLI entailment pairs on host CPU without cloud inference hops.
          </div>
        </article>

        {/* Claim Verification Distribution */}
        <article className="rx-card p-6 md:p-7 shadow-card border border-black/5">
          <div className="flex items-center justify-between pb-4 border-b border-[#F2EFE8]">
            <h3 className="font-serif text-lg font-semibold text-[#0C0C12]">
              Claim Verification Distribution
            </h3>
            <span className="text-xs text-[#7A7870] font-mono tabular-nums">{totalClaims} total claims</span>
          </div>

          <div className="my-5 space-y-4">
            <div>
              <div className="flex justify-between text-xs mb-1">
                <span className="font-medium text-[#15803D]">Supported Claims (Entailment)</span>
                <span className="font-mono text-[#15803D] tabular-nums">{supportedClaims} ({suppPct}%)</span>
              </div>
              <div className="h-2 w-full bg-[#FAF8F3] rounded-full overflow-hidden border border-[#EBE7DC]">
                <div className="h-full bg-[#15803D] rounded-full transition-all duration-300" style={{ width: `${suppPct}%` }} />
              </div>
            </div>

            <div>
              <div className="flex justify-between text-xs mb-1">
                <span className="font-medium text-[#DC2626]">Contradicted Claims (Hallucinations)</span>
                <span className="font-mono text-[#DC2626] tabular-nums">{contradictedClaims} ({contPct}%)</span>
              </div>
              <div className="h-2 w-full bg-[#FAF8F3] rounded-full overflow-hidden border border-[#EBE7DC]">
                <div className="h-full bg-[#DC2626] rounded-full transition-all duration-300" style={{ width: `${contPct}%` }} />
              </div>
            </div>

            <div>
              <div className="flex justify-between text-xs mb-1">
                <span className="font-medium text-[#7A7870]">Ungrounded Statements</span>
                <span className="font-mono text-[#7A7870] tabular-nums">{ungroundedClaims} ({ungrPct}%)</span>
              </div>
              <div className="h-2 w-full bg-[#FAF8F3] rounded-full overflow-hidden border border-[#EBE7DC]">
                <div className="h-full bg-[#7A7870] rounded-full transition-all duration-300" style={{ width: `${ungrPct}%` }} />
              </div>
            </div>
          </div>

          <div className="pt-3 border-t border-[#F2EFE8] text-xs text-[#7A7870]">
            Logged across all reverse-proxy sessions in local persistent SQLite audit store.
          </div>
        </article>
      </section>
    </div>
  );
};
