import { useState, useEffect, useRef } from 'react';
import type { MetricSummary } from '../types';
import { TelemetryKpiBar } from './TelemetryKpiBar';
import { SandboxView } from './SandboxView';
import { AdversarialMatrixView } from './AdversarialMatrixView';
import { TraceExplorerView } from './TraceExplorerView';
import { AnalyticsView } from './AnalyticsView';
import { RAGCompanionView } from './RAGCompanionView';

interface FullDashboardViewProps {
  initialTraceId?: string;
  onBack: () => void;
  apiBase?: string;
}

export function FullDashboardView({ initialTraceId = '', onBack, apiBase = '' }: FullDashboardViewProps) {
  const [activeTab, setActiveTab] = useState<'traces' | 'sandbox' | 'adversarial' | 'analytics' | 'companion'>(
    initialTraceId ? 'traces' : 'traces'
  );
  const [metrics, setMetrics] = useState<MetricSummary | null>(null);
  const [isOnline, setIsOnline] = useState<boolean>(false);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [globalSearch, setGlobalSearch] = useState<string>(initialTraceId);
  const [isResetting, setIsResetting] = useState<boolean>(false);

  const searchInputRef = useRef<HTMLInputElement>(null);

  const fetchMetrics = async () => {
    setIsRefreshing(true);
    try {
      const res = await fetch(`${apiBase}/v1/metrics`);
      if (res.ok) {
        const data = await res.json();
        setMetrics(data);
        setIsOnline(true);
      } else {
        setIsOnline(false);
      }
    } catch {
      setIsOnline(false);
    } finally {
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    fetchMetrics();
    const interval = setInterval(fetchMetrics, 10000);
    return () => clearInterval(interval);
  }, []);

  const handleExportAuditLogs = () => {
    window.open(`${apiBase}/v1/traces?limit=500`, '_blank');
  };

  const handleResetSession = async () => {
    if (window.confirm('Reset all audit traces and KPI telemetry to start a fresh demo session?')) {
      setIsResetting(true);
      try {
        await fetch(`${apiBase}/v1/traces/clear`, { method: 'POST' });
        await fetchMetrics();
      } catch (err) {
        console.error('Failed to reset session traces:', err);
      } finally {
        setIsResetting(false);
      }
    }
  };

  return (
    <div className="h-screen w-screen overflow-y-auto bg-[#F5F3EE] p-3 md:p-6 lg:p-8 flex items-center justify-center font-sans">
      <div className="dashboard-shell w-full max-w-[1580px] rounded-[32px] shadow-float overflow-hidden flex flex-col lg:flex-row min-h-[min(920px,calc(100dvh-2.5rem))] lg:min-h-[880px] bg-white border border-[#D9D4C7]">
        {/* Left Sidebar */}
        <aside className="w-full lg:w-[260px] xl:w-[280px] bg-[#E8E4DA]/60 border-r border-[#D9D4C7]/70 p-6 flex flex-col justify-between shrink-0">
          <div className="space-y-6">
            {/* Back Button */}
            <button
              type="button"
              onClick={onBack}
              className="w-full flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-semibold text-[#0C0C12] bg-white border border-[#D9D4C7] hover:bg-[#F6F5F1] transition-colors shadow-sm"
            >
              <svg width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2.2" viewBox="0 0 24 24">
                <path d="M19 12H5M12 19l-7-7 7-7" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              <span>Back to Chatbot</span>
            </button>

            {/* Logo */}
            <div className="flex items-center gap-3 px-2 pt-1">
              <svg width="24" height="24" fill="none" viewBox="0 0 28 28" className="shrink-0">
                <path d="M14 4C14.8 4 15.5 4.7 15.5 5.5V8.5C15.5 9.3 14.8 10 14 10C13.2 10 12.5 9.3 12.5 8.5V5.5C12.5 4.7 13.2 4 14 4Z" fill="#0C0C12" />
                <path d="M14 18C14.8 18 15.5 18.7 15.5 19.5V22.5C15.5 23.3 14.8 24 14 24C13.2 24 12.5 23.3 12.5 22.5V19.5C12.5 18.7 13.2 18 14 18Z" fill="#0C0C12" />
                <path d="M5.5 12.5H8.5C9.3 12.5 10 13.2 10 14C10 14.8 9.3 15.5 8.5 15.5H5.5C4.7 15.5 4 14.8 4 14C4 13.2 4.7 12.5 5.5 12.5Z" fill="#0C0C12" />
                <path d="M19.5 12.5H22.5C23.3 12.5 24 13.2 24 14C24 14.8 23.3 15.5 22.5 15.5H19.5C18.7 15.5 18 14.8 18 14C18 13.2 18.7 12.5 19.5 12.5Z" fill="#0C0C12" />
                <circle cx="14" cy="14" fill="#0C0C12" r="3.2" />
                <circle cx="8" cy="8" fill="#0C0C12" r="2" />
                <circle cx="20" cy="8" fill="#0C0C12" r="2" />
                <circle cx="8" cy="20" fill="#0C0C12" r="2" />
                <circle cx="20" cy="20" fill="#0C0C12" r="2" />
              </svg>
              <div>
                <span className="font-serif text-lg font-semibold tracking-tight text-[#0C0C12] block">
                  Hearsay
                </span>
                <span className="text-[10px] text-[#7A7870] font-medium tracking-wide uppercase">
                  Full Telemetry Audit
                </span>
              </div>
            </div>

            {/* Nav */}
            <div className="space-y-1">
              <p className="text-[11px] font-medium tracking-wider text-[#7A7870] uppercase px-3 mb-2">
                Verification Navigation
              </p>
              <nav className="space-y-1">
                {[
                  { id: 'traces', label: 'Trace Explorer' },
                  { id: 'analytics', label: 'System Reliability' },
                  { id: 'adversarial', label: 'Adversarial Matrix' },
                  { id: 'sandbox', label: 'Verification Sandbox' },
                  { id: 'companion', label: 'Raw Benchmark Test' },
                ].map((t) => (
                  <button
                    key={t.id}
                    type="button"
                    onClick={() => setActiveTab(t.id as any)}
                    className={`w-full text-left px-3.5 py-2.5 rounded-xl text-xs transition-colors duration-150 ${
                      activeTab === t.id
                        ? 'bg-white shadow-sm font-semibold text-[#0C0C12] border border-[#E5E1D8]'
                        : 'text-[#65635C] hover:text-[#0C0C12] hover:bg-white/40'
                    }`}
                  >
                    {t.label}
                  </button>
                ))}
              </nav>
            </div>
          </div>

          {/* Engine spec info */}
          <div className="p-3 bg-white/70 rounded-xl border border-[#D9D4C7]/80 text-xs space-y-1">
            <div className="flex items-center justify-between">
              <span className="text-[#7A7870]">Engine:</span>
              <span className="font-medium text-[#0C0C12]">DeBERTa-v3 NLI</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-[#7A7870]">Local Port:</span>
              <span className="font-mono text-[#0C0C12]">8000</span>
            </div>
          </div>
        </aside>

        {/* Main Dashboard Content */}
        <main className="flex-1 p-5 md:p-8 overflow-y-auto space-y-6 bg-white/40">
          {/* Top Bar */}
          <section className="flex flex-col md:flex-row items-stretch md:items-center justify-between gap-4">
            <div className="relative flex-1 max-w-xl">
              <input
                ref={searchInputRef}
                type="text"
                value={globalSearch}
                onChange={(e) => {
                  setGlobalSearch(e.target.value);
                  if (activeTab !== 'traces') setActiveTab('traces');
                }}
                placeholder="Search audit traces or request ID..."
                className="w-full pl-4 pr-10 py-2 bg-white rounded-full border border-black/10 text-xs text-[#0C0C12] placeholder-[#9A9890] shadow-sm focus:outline-none focus:ring-2 focus:ring-[#0C0C12]/15"
              />
            </div>

            <div className="flex items-center gap-3">
              <div className="inline-flex items-center gap-2 px-3 py-1.5 bg-white rounded-full border border-black/5 text-xs text-[#0C0C12]">
                <span className={`w-2 h-2 rounded-full ${isOnline ? 'bg-[#15803D]' : 'bg-[#DC2626]'}`} />
                <span>{isOnline ? 'Gateway: 8000 Live' : 'Gateway Offline'}</span>
              </div>
              <button
                type="button"
                onClick={fetchMetrics}
                disabled={isRefreshing}
                className="px-3.5 py-1.5 bg-white rounded-full border border-black/5 text-xs font-medium text-[#0C0C12] hover:bg-[#F6F5F1]"
              >
                {isRefreshing ? 'Refreshing...' : 'Refresh'}
              </button>
              <button
                type="button"
                onClick={handleResetSession}
                disabled={isResetting}
                className="px-3.5 py-1.5 bg-white rounded-full border border-black/5 text-xs font-medium text-[#DC2626] hover:bg-[#FEF2F2]"
              >
                Reset
              </button>
              <button
                type="button"
                onClick={handleExportAuditLogs}
                className="bg-[#0C0C12] text-white text-xs font-medium px-4 py-1.5 rounded-full hover:bg-black"
              >
                Export Logs
              </button>
            </div>
          </section>

          {/* KPI Bar */}
          <TelemetryKpiBar metrics={metrics} isOnline={isOnline} />

          {/* Active Tab View */}
          <section className="space-y-6">
            {activeTab === 'traces' && <TraceExplorerView initialSearch={globalSearch} />}
            {activeTab === 'analytics' && <AnalyticsView metrics={metrics} />}
            {activeTab === 'adversarial' && <AdversarialMatrixView />}
            {activeTab === 'sandbox' && <SandboxView onVerificationSuccess={() => fetchMetrics()} />}
            {activeTab === 'companion' && (
              <RAGCompanionView
                apiBase={apiBase}
                onNavigateToTrace={(reqId) => {
                  setGlobalSearch(reqId);
                  setActiveTab('traces');
                }}
              />
            )}
          </section>
        </main>
      </div>
    </div>
  );
}
