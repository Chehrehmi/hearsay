import type { MetricSummary } from '../types';
import { formatPercentage, clampPercentage } from '../utils/formatters';

interface TelemetryKpiBarProps {
  metrics: MetricSummary | null;
  isOnline: boolean;
}

export const TelemetryKpiBar = ({ metrics, isOnline }: TelemetryKpiBarProps) => {
  const total = metrics?.total_requests ?? 0;
  const passRate = metrics?.verification_pass_rate ?? 0;
  const avgScore = metrics?.avg_groundedness_score ?? 0;
  const p50 = metrics?.p50_latency_ms ?? metrics?.avg_latency_ms ?? 0;
  const p95 = metrics?.p95_latency_ms ?? (Number(p50) * 1.4).toFixed(0);
  const hallucinations = metrics?.total_hallucinations ?? 0;
  const verifiedCount = metrics?.total_verified ?? 0;

  const scoreNum = clampPercentage(avgScore);
  // Segmented 20-pill bar representation
  const activePills = Math.min(20, Math.max(0, Math.round((scoreNum / 100) * 20)));

  return (
    <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
      {/* 1. Groundedness Score & Segmented Micro-Bar */}
      <article className="rx-card p-5 flex flex-col justify-between">
        <div>
          <div className="flex items-center justify-between gap-2">
            <span className="text-xs font-medium text-[#7A7870] leading-none">Groundedness Index</span>
            <span className={`inline-flex items-center justify-center px-2.5 py-1 rounded-full text-[10px] font-semibold leading-none tracking-tight shrink-0 ${
              scoreNum >= 80 ? 'bg-[#E8F8D6] text-[#2F6B12]' : 'bg-[#FEF3C7] text-[#92400E]'
            }`}>
              {scoreNum >= 80 ? 'High Confidence' : 'Review Required'}
            </span>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="font-serif text-3xl font-semibold tracking-tight text-[#0C0C12]">
              {formatPercentage(avgScore)}
            </span>
            <span className="text-xs text-[#7A7870]">
              mean score
            </span>
          </div>
        </div>

        {/* 20 Segmented Micro-Pills */}
        <div className="mt-4 pt-3 border-t border-[#F5F2EB]">
          <div className="flex items-center gap-1 overflow-hidden">
            {Array.from({ length: 20 }).map((_, idx) => (
              <span
                key={idx}
                className={`h-3 flex-1 rounded-full ${
                  idx < activePills
                    ? 'bg-[#BD47F2]'
                    : 'bg-[#EAE7DF]'
                }`}
              />
            ))}
          </div>
          <div className="flex justify-between text-[10px] text-[#8C887E] mt-1.5 font-medium">
            <span>Pass rate: {formatPercentage(passRate)}</span>
            <span>{verifiedCount} / {total} verified</span>
          </div>
        </div>
      </article>

      {/* 2. Runtime Inference Latency */}
      <article className="rx-card p-5 flex flex-col justify-between">
        <div>
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-[#7A7870]">Inference Latency</span>
            <span className="text-[11px] font-mono text-[#5F5D56] bg-[#F1EFEA] px-2 py-0.5 rounded-md">
              P50 / P95
            </span>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="font-serif text-3xl font-semibold tracking-tight text-[#0C0C12]">
              {p50}
            </span>
            <span className="text-xs text-[#7A7870]">ms</span>
          </div>
        </div>

        <div className="mt-4 pt-3 border-t border-[#F5F2EB] flex items-center justify-between text-xs text-[#5F5D56]">
          <span>P95 Percentile</span>
          <span className="font-mono font-medium text-[#0C0C12]">{p95} ms</span>
        </div>
      </article>

      {/* 3. Verification Volume & Hallucinations */}
      <article className="rx-card p-5 flex flex-col justify-between">
        <div>
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-[#7A7870]">Scanned Traffic</span>
            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold bg-[#E8F8D6] text-[#2F6B12]">
              Live Feed
            </span>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="font-serif text-3xl font-semibold tracking-tight text-[#0C0C12]">
              {total}
            </span>
            <span className="text-xs text-[#7A7870]">verified requests</span>
          </div>
        </div>

        <div className="mt-4 pt-3 border-t border-[#F5F2EB] flex items-center justify-between text-xs">
          <span className="text-[#7A7870]">Hallucinations Flagged</span>
          <span className="font-mono font-semibold text-[#E11D48]">{hallucinations}</span>
        </div>
      </article>

      {/* 4. Gateway Intercept Status */}
      <article className="rx-card p-5 flex flex-col justify-between">
        <div>
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-[#7A7870]">Gateway Proxy</span>
            <div className="flex items-center gap-1.5">
              <span className={`w-2 h-2 rounded-full ${isOnline ? 'bg-[#91FE00]' : 'bg-[#E11D48]'}`} />
              <span className="text-[11px] font-medium text-[#0C0C12]">
                {isOnline ? 'Port 8000' : 'Offline'}
              </span>
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="font-serif text-3xl font-semibold tracking-tight text-[#0C0C12]">
              {isOnline ? 'Active' : 'Standby'}
            </span>
          </div>
        </div>

        <div className="mt-4 pt-3 border-t border-[#F5F2EB] flex items-center justify-between text-xs text-[#7A7870]">
          <span>Pipeline</span>
          <span className="font-medium text-[#0C0C12]">DeBERTa-v3 NLI</span>
        </div>
      </article>
    </section>
  );
};
