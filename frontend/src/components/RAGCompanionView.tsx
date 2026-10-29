import { useState, useEffect } from 'react';
import type { CuratedCorpusItem, RAGChatMessage, VerificationResult } from '../types';

interface RAGCompanionViewProps {
  apiBase: string;
  onNavigateToTrace?: (requestId: string) => void;
}

export function RAGCompanionView({ apiBase, onNavigateToTrace }: RAGCompanionViewProps) {
  const [corpusItems, setCorpusItems] = useState<CuratedCorpusItem[]>([]);
  const [selectedScenarioId, setSelectedScenarioId] = useState<string>('');
  const [mode, setMode] = useState<'corpus' | 'live'>('corpus');
  const [geminiKey, setGeminiKey] = useState<string>('');
  const [showKeyInput, setShowKeyInput] = useState<boolean>(false);
  
  // Chat state
  const [messages, setMessages] = useState<RAGChatMessage[]>([]);
  const [inputQuery, setInputQuery] = useState<string>('');
  const [activeContext, setActiveContext] = useState<string>('');
  const [isSending, setIsSending] = useState<boolean>(false);
  const [selectedMessageId, setSelectedMessageId] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Fetch curated demo corpus
  useEffect(() => {
    async function loadCorpus() {
      try {
        const res = await fetch(`${apiBase}/v1/demo/corpus`);
        if (res.ok) {
          const items: CuratedCorpusItem[] = await res.json();
          setCorpusItems(items);
          if (items.length > 0) {
            setSelectedScenarioId(items[0].id);
            setActiveContext(items[0].context);
            setInputQuery(items[0].question);
          }
        }
      } catch {
        // Fallback offline preset if gateway isn't reached yet
      }
    }
    loadCorpus();
  }, [apiBase]);

  // Handle scenario selection
  const handleSelectScenario = (scenarioId: string) => {
    setSelectedScenarioId(scenarioId);
    setErrorMessage(null);
    const item = corpusItems.find(c => c.id === scenarioId);
    if (item) {
      setActiveContext(item.context);
      setInputQuery(item.question);
    }
  };

  // Send query through Hearsay Verification Middleware
  const handleSendMessage = async () => {
    const trimmedQuery = inputQuery.trim();
    if (!trimmedQuery) return;
    if (!activeContext.trim()) {
      setErrorMessage("Retrieval context is required to verify RAG generation.");
      return;
    }

    setErrorMessage(null);
    setIsSending(true);

    const userMsgId = `msg-${Date.now()}`;
    const userMsg: RAGChatMessage = {
      id: userMsgId,
      role: 'user',
      content: trimmedQuery,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    const assistantMsgId = `asst-${Date.now() + 1}`;
    const placeholderAsst: RAGChatMessage = {
      id: assistantMsgId,
      role: 'assistant',
      content: 'Synthesizing response and executing DeBERTa verification...',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      isLoading: true,
      contextUsed: activeContext,
    };

    setMessages(prev => [...prev, userMsg, placeholderAsst]);
    setSelectedMessageId(assistantMsgId);

    try {
      let candidateResponse = "";
      const currentScenario = corpusItems.find(c => c.id === selectedScenarioId);

      // In corpus mode, check if we have the authentic benchmark response
      if (mode === 'corpus' && currentScenario && currentScenario.question.trim().toLowerCase() === trimmedQuery.toLowerCase()) {
        candidateResponse = currentScenario.expected_response;
      }

      // Headers for Gemini key if provided
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      };
      if (mode === 'live' && geminiKey.trim()) {
        headers['X-Gemini-Key'] = geminiKey.trim();
      }

      // Call Hearsay /v1/chat/completions proxy
      const payload: Record<string, any> = {
        model: mode === 'live' && geminiKey ? 'gemini-2.5-flash' : 'hearsay-verified',
        messages: [{ role: 'user', content: trimmedQuery }],
        verirag_context: {
          source_id: selectedScenarioId || 'custom-retrieval-doc',
          source_info: activeContext,
        },
      };

      if (candidateResponse) {
        payload['response_text'] = candidateResponse;
      }

      const res = await fetch(`${apiBase}/v1/chat/completions`, {
        method: 'POST',
        headers,
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || `Gateway error (${res.status})`);
      }

      const data = await res.json();
      const asstContent = data.choices?.[0]?.message?.content || candidateResponse || "Response generated.";
      const verification: VerificationResult | null = data.hearsay_verification || null;

      setMessages(prev =>
        prev.map(m =>
          m.id === assistantMsgId
            ? {
                ...m,
                content: asstContent,
                isLoading: false,
                verification,
              }
            : m
        )
      );
    } catch (err: any) {
      setErrorMessage(err.message || "Failed to communicate with Hearsay Gateway.");
      setMessages(prev =>
        prev.map(m =>
          m.id === assistantMsgId
            ? {
                ...m,
                content: "Verification failed. Please ensure Hearsay Gateway is running on port 8000.",
                isLoading: false,
              }
            : m
        )
      );
    } finally {
      setIsSending(false);
    }
  };

  const selectedMessage = messages.find(m => m.id === selectedMessageId);
  const activeVerification = selectedMessage?.verification;

  return (
    <div className="space-y-6">
      {/* Top Controls Toolbar */}
      <div className="bg-[#FAF8F3] border border-[#D9D4C7]/80 rounded-[24px] p-5 shadow-sm space-y-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h2 className="text-base font-semibold text-[#0C0C12] tracking-tight">
              Interactive RAG Chatbot Companion
            </h2>
            <p className="text-xs text-[#7A7870] mt-0.5">
              Live inline verification middleware protecting RAG responses with DeBERTa NLI cross-encoders.
            </p>
          </div>

          {/* Mode Selector & Gemini Key Pill */}
          <div className="flex items-center gap-2">
            <div className="inline-flex p-1 bg-[#E8E4DA]/60 border border-[#D9D4C7]/70 rounded-full">
              <button
                type="button"
                onClick={() => setMode('corpus')}
                className={`px-3 py-1 rounded-full text-xs font-medium transition-colors duration-150 ${
                  mode === 'corpus'
                    ? 'bg-white text-[#0C0C12] shadow-sm'
                    : 'text-[#65635C] hover:text-[#0C0C12]'
                }`}
              >
                Benchmark Mode (Safe)
              </button>
              <button
                type="button"
                onClick={() => {
                  setMode('live');
                  if (!geminiKey) setShowKeyInput(true);
                }}
                className={`px-3 py-1 rounded-full text-xs font-medium transition-colors duration-150 ${
                  mode === 'live'
                    ? 'bg-white text-[#0C0C12] shadow-sm'
                    : 'text-[#65635C] hover:text-[#0C0C12]'
                }`}
              >
                Live Gemini Proxy
              </button>
            </div>

            {mode === 'live' && (
              <button
                type="button"
                onClick={() => setShowKeyInput(!showKeyInput)}
                className="px-3 py-1.5 bg-white border border-[#D9D4C7] rounded-full text-xs text-[#0C0C12] hover:bg-[#F6F5F1] transition-colors"
              >
                {geminiKey ? 'API Key Configured ✓' : 'Set Gemini Key'}
              </button>
            )}

            {messages.length > 0 && (
              <button
                type="button"
                onClick={() => {
                  setMessages([]);
                  setSelectedMessageId(null);
                }}
                className="px-3 py-1.5 bg-white border border-[#D9D4C7] rounded-full text-xs text-[#E11D48] hover:bg-[#FFF1F2] transition-colors"
              >
                Clear Chat
              </button>
            )}
          </div>
        </div>

        {/* Live Key Input Expandable Drawer */}
        {showKeyInput && mode === 'live' && (
          <div className="p-3 bg-white border border-[#D9D4C7] rounded-xl flex items-center gap-3">
            <div className="text-xs font-medium text-[#0C0C12] shrink-0">Google AI Studio Key:</div>
            <input
              type="password"
              value={geminiKey}
              onChange={(e) => setGeminiKey(e.target.value)}
              placeholder="Paste AI Studio API Key (optional — falls back to offline extractor if empty)"
              className="flex-1 text-xs px-3 py-1.5 bg-[#FAF8F3] border border-[#D9D4C7] rounded-lg focus:outline-none focus:ring-1 focus:ring-[#BD47F2]"
            />
            <button
              type="button"
              onClick={() => setShowKeyInput(false)}
              className="px-3 py-1.5 bg-[#0C0C12] text-white text-xs rounded-lg enabled:active:scale-[0.96] transition-transform"
            >
              Save Key
            </button>
          </div>
        )}

        {/* Authentic Preset Scenario Selector */}
        <div className="flex flex-wrap items-center gap-2 pt-1 border-t border-[#D9D4C7]/50">
          <span className="text-[11px] font-medium text-[#7A7870] uppercase tracking-wider mr-1">
            Benchmarks:
          </span>
          {corpusItems.map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => handleSelectScenario(item.id)}
              className={`px-3 py-1.5 rounded-full text-xs transition-colors duration-150 ${
                selectedScenarioId === item.id
                  ? 'bg-[#0C0C12] text-white font-medium shadow-sm'
                  : 'bg-white border border-[#D9D4C7] text-[#4A4842] hover:bg-[#F6F5F1]'
              }`}
            >
              {item.title}
            </button>
          ))}
          <button
            type="button"
            onClick={() => {
              setSelectedScenarioId('custom');
              setActiveContext('');
              setInputQuery('');
            }}
            className={`px-3 py-1.5 rounded-full text-xs transition-colors duration-150 ${
              selectedScenarioId === 'custom'
                ? 'bg-[#0C0C12] text-white font-medium'
                : 'bg-white border border-[#D9D4C7] text-[#4A4842] hover:bg-[#F6F5F1]'
            }`}
          >
            Custom Document...
          </button>
        </div>
      </div>

      {/* Error alert banner */}
      {errorMessage && (
        <div className="p-3 bg-[#FFF1F2] border border-[#FECDD3] rounded-xl text-xs text-[#E11D48] flex items-center justify-between">
          <span>{errorMessage}</span>
          <button type="button" onClick={() => setErrorMessage(null)} className="font-bold ml-2">✕</button>
        </div>
      )}

      {/* Split Screen Layout: 60% Chat Timeline | 40% Telemetry & Evidence */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Column: Conversational Stream (7 cols) */}
        <div className="lg:col-span-7 bg-[#FAF8F3] border border-[#D9D4C7]/80 rounded-[24px] p-5 flex flex-col min-h-[580px] shadow-sm justify-between">
          {/* Chat Stream Header */}
          <div className="pb-3 border-b border-[#D9D4C7]/60 flex items-center justify-between">
            <span className="text-xs font-semibold text-[#0C0C12] uppercase tracking-wider">
              Conversational Session
            </span>
            <span className="text-[11px] text-[#7A7870]">
              Mode: {mode === 'corpus' ? 'Offline Benchmark Split' : 'Live Gateway Proxy'}
            </span>
          </div>

          {/* Messages Container */}
          <div className="flex-1 overflow-y-auto overscroll-contain py-4 space-y-4 max-h-[460px] pr-1">
            {messages.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center text-center p-8 text-[#7A7870] space-y-2">
                <div className="w-10 h-10 rounded-full bg-[#E8E4DA]/50 flex items-center justify-center text-[#7A7870]">
                  💬
                </div>
                <p className="text-xs font-medium text-[#0C0C12]">No conversation started yet.</p>
                <p className="text-[11px] max-w-sm">
                  Select an authentic benchmark scenario above or type a custom question to inspect Hearsay's inline groundedness verification.
                </p>
              </div>
            ) : (
              messages.map((msg) => (
                <div
                  key={msg.id}
                  className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}
                >
                  <div
                    className={`max-w-[88%] rounded-2xl p-4 text-xs md:text-sm leading-relaxed ${
                      msg.role === 'user'
                        ? 'bg-[#0C0C12] text-white shadow-sm'
                        : 'bg-white border border-[#D9D4C7]/80 text-[#0C0C12] shadow-sm'
                    }`}
                  >
                    {msg.role === 'assistant' && (
                      <div className="text-[10px] font-semibold tracking-wider text-[#7A7870] uppercase mb-1.5 flex items-center justify-between">
                        <span>RAG Assistant</span>
                        <span>{msg.timestamp}</span>
                      </div>
                    )}
                    <p className="whitespace-pre-wrap">{msg.content}</p>

                    {/* Verification Pill on Assistant Messages */}
                    {msg.role === 'assistant' && msg.verification && (
                      <div className="mt-3 pt-2.5 border-t border-[#F1EFEA] flex flex-wrap items-center justify-between gap-2">
                        <div className="flex items-center gap-1.5">
                          <span
                            className={`w-2 h-2 rounded-full ${
                              msg.verification.overall_status === 'Verified'
                                ? 'bg-[#91FE00]'
                                : 'bg-[#E11D48]'
                            }`}
                          />
                          <span
                            className={`text-[11px] font-medium ${
                              msg.verification.overall_status === 'Verified'
                                ? 'text-[#3E7B00]'
                                : 'text-[#E11D48]'
                            }`}
                          >
                            {msg.verification.overall_status === 'Verified'
                              ? '100% Grounded'
                              : 'Hallucination Intercepted'}
                          </span>
                          <span className="text-[10px] text-[#7A7870]">
                            ({msg.verification.supported_claims}/{msg.verification.total_claims} claims)
                          </span>
                        </div>

                        <button
                          type="button"
                          onClick={() => setSelectedMessageId(msg.id)}
                          className="text-[11px] font-medium text-[#BD47F2] hover:underline cursor-pointer"
                        >
                          Inspect Evidence →
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>

          {/* Input & Context Accordion Area */}
          <div className="pt-3 border-t border-[#D9D4C7]/60 space-y-3">
            {/* Expandable Context Accordion */}
            <details className="text-xs group">
              <summary className="cursor-pointer text-[11px] font-medium text-[#7A7870] hover:text-[#0C0C12] flex items-center justify-between">
                <span>View Retrieved Evidence Context ({activeContext.length} chars)</span>
                <span className="group-open:rotate-180 transition-transform">▼</span>
              </summary>
              <textarea
                value={activeContext}
                onChange={(e) => setActiveContext(e.target.value)}
                placeholder="Paste retrieved source context chunks here..."
                rows={3}
                className="w-full mt-2 p-2.5 bg-white border border-[#D9D4C7] rounded-xl text-xs text-[#0C0C12] placeholder-[#9A9890] focus:outline-none focus:ring-1 focus:ring-[#BD47F2]"
              />
            </details>

            {/* Input Bar */}
            <div className="flex gap-2">
              <input
                type="text"
                value={inputQuery}
                onChange={(e) => setInputQuery(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !isSending) {
                    handleSendMessage();
                  }
                }}
                placeholder="Ask a question against the retrieved knowledge..."
                className="flex-1 px-4 py-2.5 bg-white border border-[#D9D4C7] rounded-full text-xs md:text-sm text-[#0C0C12] placeholder-[#9A9890] shadow-sm focus:outline-none focus:ring-2 focus:ring-[#BD47F2]/20 focus:border-[#BD47F2]"
              />
              <button
                type="button"
                onClick={handleSendMessage}
                disabled={isSending || !inputQuery.trim()}
                className="px-5 py-2.5 bg-[#0C0C12] hover:bg-black text-white text-xs md:text-sm font-medium rounded-full shadow-sm transition-transform duration-150 enabled:active:scale-[0.96] disabled:opacity-40"
              >
                {isSending ? 'Verifying...' : 'Send'}
              </button>
            </div>
          </div>
        </div>

        {/* Right Column: Hearsay Evidence & Telemetry Inspector (5 cols) */}
        <div className="lg:col-span-5 bg-[#FAF8F3] border border-[#D9D4C7]/80 rounded-[24px] p-5 flex flex-col min-h-[580px] shadow-sm space-y-4">
          <div className="pb-3 border-b border-[#D9D4C7]/60 flex items-center justify-between">
            <span className="text-xs font-semibold text-[#0C0C12] uppercase tracking-wider">
              Verification Inspector
            </span>
            {activeVerification && (
              <span className="text-[11px] font-mono text-[#7A7870]">
                ID: #{activeVerification.request_id.slice(0, 8)}
              </span>
            )}
          </div>

          {!activeVerification ? (
            <div className="flex-1 flex flex-col items-center justify-center text-center p-6 text-[#7A7870] space-y-2">
              <div className="w-9 h-9 rounded-full bg-[#E8E4DA]/50 flex items-center justify-center text-[#7A7870]">
                🔍
              </div>
              <p className="text-xs font-medium text-[#0C0C12]">No Claim Selected</p>
              <p className="text-[11px] max-w-xs">
                Send a message or click "Inspect Evidence" on an assistant response to view atomic claim decomposition and NLI entailment scores.
              </p>
            </div>
          ) : (
            <div className="space-y-4 flex-1 overflow-y-auto overscroll-contain max-h-[520px] pr-1">
              {/* Telemetry Card */}
              <div className="bg-white border border-[#D9D4C7]/80 rounded-[18px] p-4 shadow-sm space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-medium text-[#7A7870] uppercase tracking-wider">
                    Verdict Status
                  </span>
                  <span
                    className={`px-2.5 py-0.5 rounded-full text-xs font-medium ${
                      activeVerification.overall_status === 'Verified'
                        ? 'bg-[#E8F8D8] text-[#2C6200]'
                        : 'bg-[#FFE4E6] text-[#E11D48]'
                    }`}
                  >
                    {activeVerification.overall_status}
                  </span>
                </div>

                <div className="grid grid-cols-3 gap-2 pt-2 border-t border-[#F1EFEA] text-center">
                  <div className="p-2 bg-[#FAF8F3] rounded-xl">
                    <div className="text-[10px] text-[#7A7870]">Groundedness</div>
                    <div className="text-sm font-semibold text-[#0C0C12]">
                      {activeVerification.groundedness_score}%
                    </div>
                  </div>
                  <div className="p-2 bg-[#FAF8F3] rounded-xl">
                    <div className="text-[10px] text-[#7A7870]">Supported</div>
                    <div className="text-sm font-semibold text-[#2C6200]">
                      {activeVerification.supported_claims}
                    </div>
                  </div>
                  <div className="p-2 bg-[#FAF8F3] rounded-xl">
                    <div className="text-[10px] text-[#7A7870]">Latency</div>
                    <div className="text-sm font-semibold text-[#0C0C12]">
                      {activeVerification.latency_ms} ms
                    </div>
                  </div>
                </div>
              </div>

              {/* Claims Breakdown List */}
              <div className="space-y-2">
                <div className="text-[11px] font-semibold text-[#7A7870] uppercase tracking-wider">
                  Decomposed Claims ({activeVerification.claims.length})
                </div>

                {activeVerification.claims.map((claim) => (
                  <div
                    key={claim.claim_id}
                    className="p-3 bg-white border border-[#D9D4C7]/80 rounded-xl space-y-2 text-xs"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <p className="font-medium text-[#0C0C12] leading-relaxed">
                        "{claim.claim_text}"
                      </p>
                      <span
                        className={`px-2 py-0.5 rounded-full text-[10px] font-medium shrink-0 ${
                          claim.status === 'Supported'
                            ? 'bg-[#E8F8D8] text-[#2C6200]'
                            : claim.status.includes('Contradiction')
                            ? 'bg-[#FFE4E6] text-[#E11D48]'
                            : 'bg-[#FEF3C7] text-[#B45309]'
                        }`}
                      >
                        {claim.status}
                      </span>
                    </div>

                    {/* NLI Entailment Logits */}
                    {claim.nli_logits && (
                      <div className="grid grid-cols-3 gap-1 pt-1.5 border-t border-[#F1EFEA] text-[10px] text-[#7A7870]">
                        <div>Entail: {(claim.nli_logits.entailment * 100).toFixed(1)}%</div>
                        <div>Neut: {(claim.nli_logits.neutral * 100).toFixed(1)}%</div>
                        <div>Contra: {(claim.nli_logits.contradiction * 100).toFixed(1)}%</div>
                      </div>
                    )}

                    {/* Evidence Snippet */}
                    {claim.evidence_span && (
                      <div className="p-2 bg-[#FAF8F3] rounded-lg text-[11px] text-[#4A4842] border-l-2 border-[#BD47F2]">
                        <span className="font-medium text-[#0C0C12]">Proof Span: </span>
                        {claim.evidence_span}
                      </div>
                    )}
                  </div>
                ))}
              </div>

              {/* Action to Deep Link into SQLite Trace Explorer */}
              {onNavigateToTrace && (
                <button
                  type="button"
                  onClick={() => onNavigateToTrace(activeVerification.request_id)}
                  className="w-full py-2.5 px-3 bg-[#E8E4DA]/60 hover:bg-[#E8E4DA] border border-[#D9D4C7] rounded-xl text-xs font-medium text-[#0C0C12] transition-colors flex items-center justify-center gap-1.5"
                >
                  <span>Inspect Audit Record in Trace Explorer</span>
                  <span>→</span>
                </button>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
