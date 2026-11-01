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
    <div className="h-screen w-screen overflow-hidden bg-[#F5F3EE] flex flex-col font-sans select-none">
      {/* Top Header Bar: Locked height, never scrolls */}
      <header className="h-14 border-b border-[#D9D4C7]/80 bg-[#FAF8F3] px-5 flex items-center justify-between shrink-0 z-10 gap-4">
        <div className="flex items-center gap-3">
          {/* Back Button */}
          <button
            type="button"
            onClick={onBack}
            className="flex items-center gap-2 px-3 py-1.5 rounded-xl text-xs font-semibold text-[#0C0C12] bg-white border border-[#D9D4C7] hover:bg-[#F6F5F1] transition-colors shadow-sm shrink-0"
          >
            <svg width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2.2" viewBox="0 0 24 24">
              <path d="M19 12H5M12 19l-7-7 7-7" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            <span>Back to Chatbot</span>
          </button>

          <div className="h-4 w-[1px] bg-[#D9D4C7] hidden sm:block" />

          {/* Logo & Subtitle */}
          <div className="flex items-center gap-2.5">
            <svg width="22" height="22" fill="none" viewBox="0 0 28 28" className="shrink-0">
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
            <span className="font-serif text-lg font-semibold tracking-tight text-[#0C0C12]">
              Hearsay
            </span>
            <span className="text-[10px] text-[#7A7870] font-semibold tracking-wider uppercase px-2 py-0.5 bg-[#E8E4DA]/60 rounded-full border border-[#D9D4C7]/60 hidden md:inline">
              Full Telemetry Audit
            </span>
          </div>
        </div>

        {/* Center / Right controls */}
        <div className="flex items-center gap-3">
          {/* Search Bar */}
          <div className="relative w-48 sm:w-64 md:w-72">
            <input
              ref={searchInputRef}
              type="text"
              value={globalSearch}
              onChange={(e) => {
                setGlobalSearch(e.target.value);
                if (activeTab !== 'traces') setActiveTab('traces');
              }}
              placeholder="Search traces or request ID..."
              className="w-full pl-3 pr-7 py-1.5 bg-white rounded-lg border border-[#D9D4C7] text-xs text-[#0C0C12] placeholder-[#9A9890] shadow-sm focus:outline-none focus:ring-1 focus:ring-[#0C0C12]"
            />
            {globalSearch && (
              <button
                type="button"
                onClick={() => setGlobalSearch('')}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-[#9A9890] hover:text-[#0C0C12] text-xs"
              >
                ✕
              </button>
            )}
          </div>

          {/* Gateway Status */}
          <div className="hidden lg:inline-flex items-center gap-2 px-3 py-1.5 bg-white rounded-full border border-[#D9D4C7] text-xs text-[#0C0C12]">
            <span className={`w-2 h-2 rounded-full ${isOnline ? 'bg-[#15803D]' : 'bg-[#DC2626]'}`} />
            <span>{isOnline ? 'Gateway: 8000 Live' : 'Gateway Offline'}</span>
          </div>

          {/* Action buttons */}
          <button
            type="button"
            onClick={fetchMetrics}
            disabled={isRefreshing}
            className="p-1.5 bg-white hover:bg-[#F6F5F1] rounded-lg border border-[#D9D4C7] text-[#0C0C12] transition-colors"
            title="Refresh Telemetry"
          >
            <svg className={`w-4 h-4 ${isRefreshing ? 'animate-spin' : ''}`} fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
              <path d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </button>

          <button
            type="button"
            onClick={handleExportAuditLogs}
            className="hidden sm:inline-flex px-3 py-1.5 bg-white hover:bg-[#F6F5F1] rounded-lg border border-[#D9D4C7] text-xs font-medium text-[#0C0C12] transition-colors"
          >
            Export Logs
          </button>

          <button
            type="button"
            onClick={handleResetSession}
            disabled={isResetting}
            className="hidden sm:inline-flex px-3 py-1.5 bg-[#FFF1F2] hover:bg-[#FFE4E6] text-[#DC2626] rounded-lg border border-[#FECDD3] text-xs font-medium transition-colors"
          >
            {isResetting ? 'Resetting...' : 'Reset'}
          </button>
        </div>
      </header>

      {/* Main 2-Column Body */}
      <div className="flex-1 flex overflow-hidden min-h-0">
        {/* Left Sidebar: Fixed width, scrolls independently if needed */}
        <aside className="w-56 xl:w-64 bg-[#E8E4DA]/50 border-r border-[#D9D4C7]/80 p-4 flex flex-col justify-between shrink-0 h-full overflow-y-auto min-h-0">
          <div className="space-y-4">
            <p className="text-[10px] font-semibold tracking-wider text-[#7A7870] uppercase px-2">
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
                      ? 'bg-white shadow-sm font-semibold text-[#0C0C12] border border-[#D9D4C7]'
                      : 'text-[#65635C] hover:text-[#0C0C12] hover:bg-white/40'
                  }`}
                >
                  {t.label}
                </button>
              ))}
            </nav>
          </div>

          {/* Engine spec info pinned at bottom */}
          <div className="p-3 bg-white/70 rounded-xl border border-[#D9D4C7]/80 text-[11px] space-y-1.5 mt-4 shrink-0">
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

        {/* Main Stage: Dedicated independent scroll container */}
        <main className="flex-1 h-full overflow-y-auto min-h-0 p-5 md:p-8 space-y-6 bg-white/40">
          <div className="max-w-7xl mx-auto space-y-6">
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
          </div>
        </main>
      </div>
    </div>
  );
}
