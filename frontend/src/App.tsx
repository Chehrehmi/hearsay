import { useState, useEffect, useRef } from 'react';
import type { MetricSummary } from './types';
import { TelemetryKpiBar } from './components/TelemetryKpiBar';
import { SandboxView } from './components/SandboxView';
import { AdversarialMatrixView } from './components/AdversarialMatrixView';
import { TraceExplorerView } from './components/TraceExplorerView';
import { AnalyticsView } from './components/AnalyticsView';
import { RAGCompanionView } from './components/RAGCompanionView';

export function App() {
  const [activeTab, setActiveTab] = useState<'companion' | 'sandbox' | 'adversarial' | 'traces' | 'analytics'>('companion');
  const [metrics, setMetrics] = useState<MetricSummary | null>(null);
  const [isOnline, setIsOnline] = useState<boolean>(false);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [globalSearch, setGlobalSearch] = useState<string>('');
  const [isMac, setIsMac] = useState<boolean>(true);

  const searchInputRef = useRef<HTMLInputElement>(null);

  // Platform detection for Cmd+K vs Ctrl+K
  useEffect(() => {
    if (typeof navigator !== 'undefined') {
      const platform = (navigator as any).userAgentData?.platform || navigator.platform || navigator.userAgent || '';
      setIsMac(/Mac|iPhone|iPod|iPad/i.test(platform));
    }
  }, []);

  // Global keyboard shortcut: Cmd+K / Ctrl+K to focus search
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        searchInputRef.current?.focus();
        searchInputRef.current?.select();
      }
      if (e.key === 'Escape' && document.activeElement === searchInputRef.current) {
        searchInputRef.current?.blur();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const apiBase = typeof window !== 'undefined' && window.location.port === '5173' ? 'http://localhost:8000' : '';

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

  return (
    <div className="p-3 md:p-6 lg:p-8 flex items-center justify-center min-h-screen">
      {/* RevenueX Porcelain Shell */}
      <div className="dashboard-shell w-full max-w-[1580px] rounded-[38px] shadow-float overflow-hidden flex flex-col lg:flex-row min-h-[min(920px,calc(100dvh-2.5rem))] lg:min-h-[880px]">
        {/* Left Sidebar */}
        <aside className="w-full lg:w-[260px] xl:w-[280px] bg-[#E8E4DA]/60 border-r border-[#D9D4C7]/70 p-6 flex flex-col justify-between shrink-0">
          <div className="space-y-6">
            {/* Logo & Brand Wordmark */}
            <div className="flex items-center gap-3 px-2 pt-1">
              <div className="w-8 h-8 rounded-full flex items-center justify-center text-[#0C0C12] shrink-0" style={{ width: '32px', height: '32px' }}>
                <svg className="w-7 h-7" width="28" height="28" fill="none" viewBox="0 0 28 28">
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
              </div>
              <span className="font-serif text-[22px] font-semibold tracking-tight text-[#0C0C12]">
                Hearsay
              </span>
            </div>

            {/* Main Navigation */}
            <div className="space-y-1">
              <p className="text-[11px] font-medium tracking-wider text-[#7A7870] uppercase px-3 mb-2">
                Main
              </p>
              <nav aria-label="Main Navigation" className="space-y-1">
                <button
                  onClick={() => setActiveTab('companion')}
                  className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-2xl text-sm transition-colors duration-150 ${
                    activeTab === 'companion'
                      ? 'bg-white shadow-sm font-medium text-[#0C0C12]'
                      : 'text-[#65635C] hover:text-[#0C0C12] hover:bg-white/40 font-normal'
                  }`}
                >
                  <svg className="w-4 h-4 text-[#BD47F2] shrink-0" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                    <path d="M21 11.5a8.38 8.38 0 01-.9 3.8 8.5 8.5 0 01-7.6 4.7 8.38 8.38 0 01-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 01-.9-3.8 8.5 8.5 0 014.7-7.6 8.38 8.38 0 013.8-.9h.5a8.48 8.48 0 018 8v.5z" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                  <span>RAG Companion</span>
                </button>

                <button
                  onClick={() => setActiveTab('sandbox')}
                  className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-2xl text-sm transition-colors duration-150 ${
                    activeTab === 'sandbox'
                      ? 'bg-white shadow-sm font-medium text-[#0C0C12]'
                      : 'text-[#65635C] hover:text-[#0C0C12] hover:bg-white/40 font-normal'
                  }`}
                >
                  <svg className="w-4 h-4 text-[#0C0C12] shrink-0" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                    <rect height="7" rx="1.5" width="7" x="3" y="3" />
                    <rect height="7" rx="1.5" width="7" x="14" y="3" />
                    <rect height="7" rx="1.5" width="7" x="14" y="14" />
                    <rect height="7" rx="1.5" width="7" x="3" y="14" />
                  </svg>
                  <span>Verification Workbench</span>
                </button>

                <button
                  onClick={() => setActiveTab('adversarial')}
                  className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-2xl text-sm transition-colors duration-150 ${
                    activeTab === 'adversarial'
                      ? 'bg-white shadow-sm font-medium text-[#0C0C12]'
                      : 'text-[#65635C] hover:text-[#0C0C12] hover:bg-white/40 font-normal'
                  }`}
                >
                  <svg className="w-4 h-4 text-[#7A7870] shrink-0" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="1.8" viewBox="0 0 24 24">
                    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                  <span>Adversarial Matrix</span>
                </button>
              </nav>
            </div>

            {/* Observability Section */}
            <div className="space-y-1">
              <p className="text-[11px] font-medium tracking-wider text-[#7A7870] uppercase px-3 mb-2">
                Observability
              </p>
              <nav className="space-y-1">
                <button
                  onClick={() => setActiveTab('traces')}
                  className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-2xl text-sm transition-colors duration-150 ${
                    activeTab === 'traces'
                      ? 'bg-white shadow-sm font-medium text-[#0C0C12]'
                      : 'text-[#65635C] hover:text-[#0C0C12] hover:bg-white/40 font-normal'
                  }`}
                >
                  <svg className="w-4 h-4 text-[#7A7870] shrink-0" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="1.8" viewBox="0 0 24 24">
                    <path d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                  <span>Trace Explorer</span>
                </button>

                <button
                  onClick={() => setActiveTab('analytics')}
                  className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-2xl text-sm transition-colors duration-150 ${
                    activeTab === 'analytics'
                      ? 'bg-white shadow-sm font-medium text-[#0C0C12]'
                      : 'text-[#65635C] hover:text-[#0C0C12] hover:bg-white/40 font-normal'
                  }`}
                >
                  <svg className="w-4 h-4 text-[#7A7870] shrink-0" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="1.8" viewBox="0 0 24 24">
                    <path d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                  <span>System Reliability</span>
                </button>
              </nav>
            </div>

            {/* Gateway Specification Box */}
            <div className="space-y-1">
              <p className="text-[11px] font-medium tracking-wider text-[#7A7870] uppercase px-3 mb-2">
                Gateway Engine
              </p>
              <div className="p-3 bg-white/70 rounded-2xl border border-[#D9D4C7]/80 text-xs space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="text-[#7A7870]">Engine:</span>
                  <span className="font-medium text-[#0C0C12]">DeBERTa-v3 NLI</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-[#7A7870]">Local Host:</span>
                  <span className="font-mono text-[#0C0C12]">8000</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-[#7A7870]">Mode:</span>
                  <span className="text-[#059669] font-medium">Fast Intercept</span>
                </div>
              </div>
            </div>
          </div>

          {/* SQLite Export Card */}
          <div className="mt-8 pt-4 border-t border-[#D9D4C7]/80">
            <button
              onClick={handleExportAuditLogs}
              className="w-full flex items-center justify-between p-2.5 rounded-2xl hover:bg-white/60 transition-colors text-left group"
            >
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-[#DBD7CC] flex items-center justify-center text-[#55534B] shrink-0" style={{ width: '32px', height: '32px' }}>
                  <svg className="w-4 h-4" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                    <path d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </div>
                <div>
                  <div className="text-xs font-semibold text-[#0C0C12] leading-snug">Export SQLite Logs</div>
                  <div className="text-[11px] text-[#7A7870] leading-snug">JSON Audit Dump</div>
                </div>
              </div>
              <svg className="w-4 h-4 text-[#8C887E] group-hover:text-[#0C0C12] transition-colors shrink-0" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                <path d="M9 5l7 7-7 7" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </button>
          </div>
        </aside>

        {/* Main Dashboard Stage */}
        <main className="flex-1 p-5 md:p-8 overflow-y-auto space-y-7 bg-white/40">
          {/* Top Header Bar */}
          <section className="flex flex-col md:flex-row items-stretch md:items-center justify-between gap-4">
            {/* Search Input with Dynamic ⌘ + K / Ctrl + K Shortcut */}
            <div className="relative flex-1 max-w-xl">
              <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none text-[#7D7B74]">
                <svg className="w-4 h-4" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                  <path d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </div>
              <input
                ref={searchInputRef}
                type="text"
                value={globalSearch}
                onChange={(e) => {
                  setGlobalSearch(e.target.value);
                  if (activeTab !== 'traces') {
                    setActiveTab('traces');
                  }
                }}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && activeTab !== 'traces') {
                    setActiveTab('traces');
                  }
                }}
                placeholder="Search audit traces, ground truth citations, or claims..."
                className="w-full pl-11 pr-24 py-2.5 bg-white rounded-full border border-black/5 text-xs md:text-sm text-[#0C0C12] placeholder-[#9A9890] shadow-sm focus:outline-none focus:ring-2 focus:ring-[#BD47F2]/20 focus:border-[#BD47F2] transition-colors"
              />
              <div className="absolute inset-y-0 right-0 pr-2.5 flex items-center">
                <button
                  type="button"
                  onClick={() => searchInputRef.current?.focus()}
                  className="text-[11px] font-medium text-[#7D7B74] hover:text-[#0C0C12] bg-[#F1EFEA] hover:bg-[#EAE7DF] border border-[#E2DFD7] px-2 py-0.5 rounded-lg flex items-center gap-1 transition-colors cursor-pointer select-none"
                  title={isMac ? "Press ⌘K to search" : "Press Ctrl+K to search"}
                >
                  {isMac ? (
                    <>
                      <kbd className="font-sans text-[11px]">⌘</kbd>
                      <kbd className="font-sans text-[11px]">K</kbd>
                    </>
                  ) : (
                    <>
                      <kbd className="font-sans text-[10px]">Ctrl</kbd>
                      <kbd className="font-sans text-[10px]">K</kbd>
                    </>
                  )}
                </button>
              </div>
            </div>

            {/* Top Right Controls */}
            <div className="flex items-center justify-end gap-3">
              {/* Proxy Radar Indicator */}
              <div className="inline-flex items-center gap-2 px-3 py-1.5 bg-white rounded-full border border-black/5 shadow-pill text-xs font-medium text-[#0C0C12]">
                <span className={`w-2 h-2 rounded-full ${isOnline ? 'bg-[#91FE00]' : 'bg-[#E11D48]'}`} />
                <span>{isOnline ? 'Gateway: 8000 Live' : 'Gateway: Offline'}</span>
              </div>

              {/* Refresh Action */}
              <button
                onClick={fetchMetrics}
                disabled={isRefreshing}
                className="inline-flex items-center gap-1.5 px-3.5 py-2 bg-white rounded-full border border-black/5 shadow-pill text-xs font-medium text-[#0C0C12] hover:bg-[#F6F5F1] transition-colors"
              >
                <svg className={`w-3.5 h-3.5 text-[#5F5D56] ${isRefreshing ? 'animate-spin' : ''}`} width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                  <path d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
                <span>Refresh</span>
              </button>

              {/* Export Data Action */}
              <button
                onClick={handleExportAuditLogs}
                className="flex items-center gap-2 bg-[#0C0C12] hover:bg-black text-white text-xs md:text-sm font-medium px-4 py-2.5 rounded-full shadow-sm transition-transform duration-150 active:scale-95"
              >
                <span>Export Data</span>
                <svg className="w-4 h-4" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2.2" viewBox="0 0 24 24">
                  <path d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </button>
            </div>
          </section>

          {/* Telemetry KPI Bar */}
          <TelemetryKpiBar metrics={metrics} isOnline={isOnline} />

          {/* Tab Content Stage */}
          <section className="space-y-6">
            {activeTab === 'companion' && (
              <RAGCompanionView
                apiBase={apiBase}
                onNavigateToTrace={(reqId) => {
                  setGlobalSearch(reqId);
                  setActiveTab('traces');
                }}
              />
            )}
            {activeTab === 'sandbox' && (
              <SandboxView onVerificationSuccess={() => fetchMetrics()} />
            )}
            {activeTab === 'adversarial' && <AdversarialMatrixView />}
            {activeTab === 'traces' && <TraceExplorerView initialSearch={globalSearch} />}
            {activeTab === 'analytics' && <AnalyticsView metrics={metrics} />}
          </section>

          {/* Academic Project Footer */}
          <footer className="pt-6 border-t border-[#D9D4C7]/70 flex flex-col sm:flex-row items-center justify-between text-xs text-[#7A7870] gap-2">
            <div>
              Department of Computer Science & Engineering · Cochin University of Science and Technology
            </div>
            <div>
              Adversarially-Robust Runtime RAG Groundedness Gateway
            </div>
          </footer>
        </main>
      </div>
    </div>
  );
}

export default App;
