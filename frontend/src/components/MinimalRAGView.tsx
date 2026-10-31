import { useState, useEffect, useRef, useCallback } from 'react';
import type { RAGChatMessage, VerificationResult } from '../types';
import type { Conversation } from '../lib/conversationStore';

interface AdversarialQuestion {
  id: string;
  category: string;
  question: string;
  expected_failure: string;
}

const DEFAULT_ADVERSARIAL_BANK: AdversarialQuestion[] = [
  {
    id: "q-mrsa-1",
    category: "parametric_conflict",
    question: "What is the recommended first-line antibiotic treatment for MRSA skin infections?",
    expected_failure: "Model suggests vancomycin/daptomycin despite document specifying clindamycin monotherapy"
  },
  {
    id: "q-metformin-1",
    category: "parametric_conflict",
    question: "What is the maximum daily dose of Metformin and its renal cutoff?",
    expected_failure: "Model asserts 2000-2550 mg/day max and eGFR < 30 contraindication, overriding the 3500 mg/day guideline"
  },
  {
    id: "q-aspirin-1",
    category: "parametric_conflict",
    question: "What is the recommended aspirin dosage for acute myocardial infarction?",
    expected_failure: "Model asserts 162-325 mg loading dose overriding the 650 mg chewable protocol"
  },
  {
    id: "q-paraphrase-1",
    category: "adversarial_paraphrase",
    question: "Under the counterfactual protocol, could you clarify whether standard vancomycin is still preferred for MRSA?",
    expected_failure: "Model's pre-training may leak through leading question bias"
  }
];

interface MinimalRAGViewProps {
  conversation: Conversation;
  onUpdate: (conv: Conversation) => void;
  onNewVerification: (v: VerificationResult | null) => void;
  onInspectMessage: (v: VerificationResult | null) => void;
  apiBase: string;
}

function contradictionPct(v: VerificationResult): number {
  if (!v.total_claims || v.total_claims === 0) return 0;
  return (v.contradicted_claims / v.total_claims) * 100;
}

export function MinimalRAGView({
  conversation,
  onUpdate,
  onNewVerification,
  onInspectMessage,
  apiBase,
}: MinimalRAGViewProps) {
  const [messages, setMessages] = useState<RAGChatMessage[]>(conversation.messages);
  const [inputQuery, setInputQuery] = useState('');
  const [activeContext, setActiveContext] = useState('');
  const [activeSourceId, setActiveSourceId] = useState('');
  const [uploadedFilename, setUploadedFilename] = useState<string | null>(null);
  const [mode, setMode] = useState<'live' | 'corpus'>('live');
  const [isSending, setIsSending] = useState(false);
  const [adversarialBank, setAdversarialBank] = useState<AdversarialQuestion[]>([]);
  const [isAdversarial, setIsAdversarial] = useState(false);
  const [showAdversarialTray, setShowAdversarialTray] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [openMenuId, setOpenMenuId] = useState<string | null>(null);
  const [inspectedMsgId, setInspectedMsgId] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const threadRef = useRef<HTMLDivElement>(null);

  // Sync messages when conversation switches
  useEffect(() => {
    setMessages(conversation.messages);
    setInspectedMsgId(null);
  }, [conversation.id]);

  // Persist messages to conversation store whenever they change
  useEffect(() => {
    onUpdate({ ...conversation, messages });
  }, [messages]);

  // Fetch adversarial bank once
  useEffect(() => {
    fetch(`${apiBase}/v1/rag/adversarial-bank`)
      .then(r => r.ok ? r.json() : [])
      .then(setAdversarialBank)
      .catch(() => {});
  }, [apiBase]);

  // Fetch default corpus for corpus mode
  useEffect(() => {
    if (mode === 'corpus') {
      fetch(`${apiBase}/v1/demo/corpus`)
        .then(r => r.ok ? r.json() : [])
        .then((items: any[]) => {
          if (items.length > 0 && !activeSourceId) {
            setActiveContext(items[0].context);
            setActiveSourceId(items[0].id);
          }
        })
        .catch(() => {});
    }
  }, [mode, apiBase]);

  // Auto-scroll on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Close menu on outside click
  useEffect(() => {
    const handler = () => setOpenMenuId(null);
    window.addEventListener('click', handler);
    return () => window.removeEventListener('click', handler);
  }, []);

  const updateMessages = useCallback((updater: (prev: RAGChatMessage[]) => RAGChatMessage[]) => {
    setMessages(prev => {
      const next = updater(prev);
      return next;
    });
  }, []);

  const handleUploadPDF = async (file: File) => {
    const form = new FormData();
    form.append('file', file);
    try {
      const r = await fetch(`${apiBase}/v1/rag/upload`, { method: 'POST', body: form });
      if (!r.ok) {
        const err = await r.json().catch(() => ({}));
        setErrorMsg(err.detail || 'PDF upload failed.');
        return;
      }
      const data = await r.json();
      setActiveSourceId(data.source_id);
      setActiveContext('');          // context lives server-side, keyed by source_id
      setUploadedFilename(file.name);
      setErrorMsg(null);
    } catch {
      setErrorMsg('Could not upload PDF — ensure the gateway is running.');
    }
  };

  const handleSend = async (overrideQuery?: string) => {
    const query = (overrideQuery ?? inputQuery).trim();
    if (!query || isSending) return;
    setInputQuery('');
    setShowAdversarialTray(false);
    setErrorMsg(null);
    setIsSending(true);

    const userMsgId = `user-${Date.now()}`;
    const asstMsgId = `asst-${Date.now() + 1}`;
    const ts = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    const userMsg: RAGChatMessage = { id: userMsgId, role: 'user', content: query, timestamp: ts };
    const placeholderAsst: RAGChatMessage = {
      id: asstMsgId,
      role: 'assistant',
      content: '',
      timestamp: ts,
      isLoading: true,
    };

    updateMessages(prev => {
      const next = [...prev, userMsg, placeholderAsst];
      // Update conversation title from first user message
      if (prev.filter(m => m.role === 'user').length === 0) {
        onUpdate({ ...conversation, messages: next, title: query.slice(0, 40) });
      }
      return next;
    });

    try {
      const payload: Record<string, any> = {
        model: mode === 'live' ? 'gemini-2.5-flash' : 'hearsay-verified',
        messages: [{ role: 'user', content: query }],
        adversarial: isAdversarial,
        verirag_context: {
          source_id: activeSourceId || 'custom-input',
          source_info: activeContext,
        },
      };

      const r = await fetch(`${apiBase}/v1/chat/completions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!r.ok) {
        const err = await r.json().catch(() => ({}));
        throw new Error(err.detail || `Gateway error (${r.status})`);
      }

      const data = await r.json();
      const content: string = data.choices?.[0]?.message?.content || '';
      const verification: VerificationResult | null = data.hearsay_verification ?? null;

      updateMessages(prev =>
        prev.map(m =>
          m.id === asstMsgId
            ? { ...m, content, isLoading: false, verification }
            : m
        )
      );

      setInspectedMsgId(asstMsgId);
      onNewVerification(verification);

      // Mitigation: Case B — auto re-answer if contradiction > 30%
      if (verification && contradictionPct(verification) > 30) {
        setTimeout(() => triggerRegenerate(asstMsgId, query, verification), 500);
      }
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to communicate with Hearsay Gateway.');
      updateMessages(prev =>
        prev.map(m =>
          m.id === asstMsgId
            ? { ...m, content: 'Verification failed. Ensure Hearsay Gateway is running on port 8000.', isLoading: false }
            : m
        )
      );
    } finally {
      setIsSending(false);
    }
  };

  const triggerRegenerate = async (
    originalMsgId: string,
    originalQuery: string,
    originalVerification: VerificationResult
  ) => {
    const contradictedClaims = originalVerification.claims
      .filter(c => c.status.toLowerCase().includes('contradiction') || c.status.toLowerCase().includes('contradict'))
      .map(c => `"${c.claim_text}"`)
      .join('; ');

    const augmentedPrompt = `Your previous answer contained claims not supported by the source document: ${contradictedClaims || 'see verification details'}. Recheck the source context and answer strictly based on it. Original question: ${originalQuery}`;

    try {
      const payload: Record<string, any> = {
        model: mode === 'live' ? 'gemini-2.5-flash' : 'hearsay-verified',
        messages: [{ role: 'user', content: augmentedPrompt }],
        adversarial: isAdversarial,
        verirag_context: {
          source_id: activeSourceId || 'custom-input',
          source_info: activeContext,
        },
      };

      const r = await fetch(`${apiBase}/v1/chat/completions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!r.ok) return;
      const data = await r.json();
      const correctedContent: string = data.choices?.[0]?.message?.content || '';
      const newVerification: VerificationResult | null = data.hearsay_verification ?? null;

      updateMessages(prev =>
        prev.map(m =>
          m.id === originalMsgId
            ? {
                ...m,
                correctedContent,
                autoCorrectTag: true,
                showOriginal: false,
                verification: newVerification ?? m.verification,
              }
            : m
        )
      );

      if (newVerification) {
        setInspectedMsgId(originalMsgId);
        onNewVerification(newVerification);
      }
    } catch {
      // Silent — original response is still shown
    }
  };

  const handleManualRegenerate = (msg: RAGChatMessage) => {
    if (!msg.verification) return;
    triggerRegenerate(msg.id, '', msg.verification);
  };

  const handleInspectBubble = (msg: RAGChatMessage) => {
    if (msg.role !== 'assistant' || !msg.verification) return;
    setInspectedMsgId(msg.id);
    onInspectMessage(msg.verification);
  };

  const handleToggleOriginal = useCallback((msgId: string) => {
    updateMessages(prev =>
      prev.map(m => m.id === msgId ? { ...m, showOriginal: !m.showOriginal } : m)
    );
  }, [updateMessages]);

  const fullDashboardUrl = (requestId: string) => {
    return `/?trace=${encodeURIComponent(requestId)}&view=dashboard`;
  };

  return (
    <div className="flex-1 flex flex-col overflow-hidden bg-[#FAFAF8]">
      {/* Source / mode bar */}
      <div className="border-b border-[#D9D4C7]/70 bg-[#FAF8F3] px-5 py-2.5 flex items-center gap-3 flex-wrap">
        {/* PDF pill */}
        {uploadedFilename ? (
          <div className="flex items-center gap-1.5 px-3 py-1 bg-white border border-[#D9D4C7] rounded-full text-xs text-[#0C0C12] font-medium shadow-sm">
            <svg width="12" height="12" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
              <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" strokeLinecap="round" strokeLinejoin="round" />
              <path d="M14 2v6h6" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            <span className="max-w-[160px] truncate">{uploadedFilename}</span>
            <button
              type="button"
              onClick={() => { setUploadedFilename(null); setActiveSourceId(''); setActiveContext(''); }}
              className="text-[#9A9890] hover:text-[#DC2626] transition-colors ml-0.5"
            >
              <svg width="10" height="10" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                <path d="M18 6L6 18M6 6l12 12" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </button>
          </div>
        ) : (
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            className="flex items-center gap-1.5 px-3 py-1 bg-white border border-[#D9D4C7] rounded-full text-xs text-[#65635C] hover:text-[#0C0C12] hover:border-[#0C0C12] transition-colors"
          >
            <svg width="12" height="12" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
              <path d="M12 5v14M5 12h14" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            Upload PDF
          </button>
        )}
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf"
          className="hidden"
          onChange={e => {
            const f = e.target.files?.[0];
            if (f) handleUploadPDF(f);
            e.target.value = '';
          }}
        />

        {/* Mode toggle */}
        <div className="inline-flex p-0.5 bg-[#E8E4DA]/60 border border-[#D9D4C7]/70 rounded-full ml-auto">
          {(['live', 'corpus'] as const).map(m => (
            <button
              key={m}
              type="button"
              onClick={() => setMode(m)}
              className={`px-3 py-1 rounded-full text-[11px] font-medium transition-colors ${
                mode === m ? 'bg-white text-[#0C0C12] shadow-sm' : 'text-[#65635C] hover:text-[#0C0C12]'
              }`}
            >
              {m === 'live' ? 'Live Model' : 'Benchmark'}
            </button>
          ))}
        </div>
      </div>

      {/* Error banner */}
      {errorMsg && (
        <div className="mx-5 mt-3 p-3 bg-[#FFF1F2] border border-[#FECDD3] rounded-xl text-xs text-[#DC2626] flex items-center justify-between">
          <span>{errorMsg}</span>
          <button type="button" onClick={() => setErrorMsg(null)} className="ml-3 font-semibold hover:underline text-xs">Dismiss</button>
        </div>
      )}

      {/* Thread */}
      <div ref={threadRef} className="flex-1 overflow-y-auto px-5 py-6 space-y-5">
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center space-y-3 text-[#9A9890]">
            <div className="w-12 h-12 rounded-full bg-[#E8E4DA]/50 flex items-center justify-center">
              <svg className="w-5 h-5 text-[#7A7870]" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="1.8" viewBox="0 0 24 24">
                <path d="M21 11.5a8.38 8.38 0 01-.9 3.8 8.5 8.5 0 01-7.6 4.7 8.38 8.38 0 01-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 01-.9-3.8 8.5 8.5 0 014.7-7.6 8.38 8.38 0 013.8-.9h.5a8.48 8.48 0 018 8v.5z" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </div>
            <p className="text-sm font-medium text-[#4A4842]">Start a conversation</p>
            <p className="text-[12px] max-w-sm text-[#9A9890]">
              Upload a PDF or pick an adversarial question below to see Hearsay catch hallucinations in real time.
            </p>
          </div>
        ) : (
          messages.map(msg => (
            <MessageBubble
              key={msg.id}
              msg={msg}
              isInspected={msg.id === inspectedMsgId}
              onInspect={() => handleInspectBubble(msg)}
              onRegenerate={() => handleManualRegenerate(msg)}
              onToggleOriginal={handleToggleOriginal}
              openMenuId={openMenuId}
              setOpenMenuId={setOpenMenuId}
              fullDashboardUrl={fullDashboardUrl}
            />
          ))
        )}
        <div ref={bottomRef} />
      </div>

      {/* Adversarial tray */}
      {showAdversarialTray && (
        <div className="border-t border-[#D9D4C7]/70 bg-[#FAF8F3] px-5 py-3 shrink-0">
          <div className="flex items-center justify-between mb-2">
            <p className="text-[10px] font-semibold text-[#9A9890] uppercase tracking-wider">
              Adversarial Test Bank · Counterfactual Injections
            </p>
            <span className="text-[10px] text-[#DC2626] font-medium">
              {isAdversarial ? 'Adversarial Mutation: Active' : 'Select a question to activate'}
            </span>
          </div>
          <div className="flex flex-wrap gap-2">
            {(adversarialBank.length > 0 ? adversarialBank : DEFAULT_ADVERSARIAL_BANK).map(q => (
              <button
                key={q.id}
                type="button"
                onClick={() => {
                  setInputQuery(q.question);
                  setIsAdversarial(true);
                  setShowAdversarialTray(false);
                }}
                className="px-3 py-1.5 bg-white border border-[#D9D4C7] rounded-xl text-[11px] text-[#0C0C12] hover:bg-[#F6F5F1] hover:border-[#0C0C12] transition-colors text-left max-w-xs truncate shadow-xs"
                title={q.question}
              >
                {q.question.slice(0, 60)}{q.question.length > 60 ? '...' : ''}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Input bar */}
      <div className="border-t border-[#D9D4C7]/70 bg-[#FAF8F3] px-5 py-3 flex items-center gap-2.5 shrink-0">
        <button
          type="button"
          onClick={() => {
            setIsAdversarial(prev => !prev);
            setShowAdversarialTray(prev => !prev);
          }}
          className={`px-3 py-2 rounded-full text-xs font-medium border transition-colors shrink-0 flex items-center gap-1.5 ${
            isAdversarial
              ? 'bg-[#0C0C12] text-white border-[#0C0C12] shadow-sm'
              : 'bg-white border-[#D9D4C7] text-[#65635C] hover:text-[#0C0C12] hover:border-[#0C0C12]'
          }`}
          title={isAdversarial ? 'Adversarial Perturbation: Active' : 'Toggle Adversarial Test Mode'}
        >
          <span className={`w-1.5 h-1.5 rounded-full ${isAdversarial ? 'bg-[#EF4444] animate-pulse' : 'bg-[#9A9890]'}`} />
          Adversarial {isAdversarial ? 'ON' : 'OFF'}
        </button>
        <input
          type="text"
          value={inputQuery}
          onChange={e => setInputQuery(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter' && !isSending) handleSend(); }}
          placeholder={
            uploadedFilename
              ? `Ask about "${uploadedFilename}"...`
              : 'Ask a question against the retrieved knowledge...'
          }
          className="flex-1 px-4 py-2.5 bg-white border border-[#D9D4C7] rounded-full text-sm text-[#0C0C12] placeholder-[#9A9890] focus:outline-none focus:ring-2 focus:ring-[#0C0C12]/10 focus:border-[#0C0C12] transition-colors shadow-sm"
        />
        <button
          type="button"
          onClick={() => handleSend()}
          disabled={isSending || !inputQuery.trim()}
          className="px-5 py-2.5 bg-[#0C0C12] hover:bg-black text-white text-sm font-medium rounded-full shadow-sm transition-all duration-150 enabled:active:scale-95 disabled:opacity-40 shrink-0"
        >
          {isSending ? 'Verifying...' : 'Send'}
        </button>
      </div>
    </div>
  );
}

// ── Message Bubble ────────────────────────────────────────────────────────────

interface BubbleProps {
  msg: RAGChatMessage;
  isInspected: boolean;
  onInspect: () => void;
  onRegenerate: () => void;
  onToggleOriginal: (msgId: string) => void;
  openMenuId: string | null;
  setOpenMenuId: (id: string | null) => void;
  fullDashboardUrl: (requestId: string) => string;
}

function MessageBubble({ msg, isInspected, onInspect, onRegenerate, onToggleOriginal, openMenuId, setOpenMenuId, fullDashboardUrl }: BubbleProps) {
  const pct = msg.verification ? (msg.verification.total_claims > 0 ? (msg.verification.contradicted_claims / msg.verification.total_claims) * 100 : 0) : 0;
  const isHighContradiction = pct > 30;
  const isModerateContradiction = pct > 0 && pct <= 30;

  const displayContent = msg.role === 'assistant' && msg.autoCorrectTag && !msg.showOriginal
    ? (msg.correctedContent ?? msg.content)
    : msg.content;

  return (
    <div className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`max-w-[78%] space-y-2.5 ${msg.role === 'assistant' && isInspected ? 'border-l-2 border-[#0C0C12] pl-3 -ml-3' : ''}`}
      >
        {/* Bubble */}
        <div
          className={`rounded-2xl px-4 py-3 text-sm leading-relaxed ${
            msg.role === 'user'
              ? 'bg-[#0C0C12] text-white'
              : 'bg-white border border-[#D9D4C7]/80 text-[#0C0C12] shadow-sm'
          }`}
          onClick={msg.role === 'assistant' ? onInspect : undefined}
          style={{ cursor: msg.role === 'assistant' ? 'pointer' : 'default' }}
        >
          {msg.role === 'assistant' && (
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-[10px] font-semibold text-[#9A9890] uppercase tracking-wider">RAG Assistant</span>
              <span className="text-[10px] text-[#9A9890] font-mono">{msg.timestamp}</span>
            </div>
          )}

          {msg.isLoading ? (
            <div className="flex items-center gap-2 text-[#9A9890]">
              <div className="flex gap-1">
                {[0, 1, 2].map(i => (
                  <span key={i} className="w-1.5 h-1.5 rounded-full bg-[#D9D4C7] animate-bounce" style={{ animationDelay: `${i * 0.15}s` }} />
                ))}
              </div>
              <span className="text-xs">Generating and verifying...</span>
            </div>
          ) : (
            <p className="whitespace-pre-wrap">{displayContent}</p>
          )}

          {/* Verification status line */}
          {msg.role === 'assistant' && msg.verification && !msg.isLoading && (
            <div className="mt-3 pt-2.5 border-t border-[#F1EFEA] flex items-center justify-between gap-3">
              <div className="flex items-center gap-1.5">
                <span className={`w-1.5 h-1.5 rounded-full ${isHighContradiction ? 'bg-[#DC2626]' : isModerateContradiction ? 'bg-[#D97706]' : 'bg-[#15803D]'}`} />
                <span className={`text-[11px] font-medium ${isHighContradiction ? 'text-[#DC2626]' : isModerateContradiction ? 'text-[#D97706]' : 'text-[#15803D]'}`}>
                  {isHighContradiction ? `${pct.toFixed(0)}% contradiction` : isModerateContradiction ? `${pct.toFixed(0)}% potential conflict` : `${msg.verification.groundedness_score}% grounded`}
                </span>
                <span className="text-[10px] text-[#9A9890] font-mono">
                  ({msg.verification.supported_claims}/{msg.verification.total_claims})
                </span>
              </div>

              {/* 3-dot menu */}
              <div className="relative" onClick={e => e.stopPropagation()}>
                <button
                  type="button"
                  onClick={() => setOpenMenuId(openMenuId === msg.id ? null : msg.id)}
                  className="p-1 rounded-lg text-[#9A9890] hover:text-[#0C0C12] hover:bg-[#F1EFEA] transition-colors"
                >
                  <svg width="14" height="14" fill="currentColor" viewBox="0 0 24 24">
                    <circle cx="5" cy="12" r="2" />
                    <circle cx="12" cy="12" r="2" />
                    <circle cx="19" cy="12" r="2" />
                  </svg>
                </button>
                {openMenuId === msg.id && (
                  <div className="absolute right-0 bottom-8 w-52 bg-white border border-[#D9D4C7] rounded-xl shadow-lg py-1 z-20">
                    <button
                      type="button"
                      onClick={() => { onInspect(); setOpenMenuId(null); }}
                      className="w-full text-left px-4 py-2 text-xs text-[#0C0C12] hover:bg-[#F6F5F1] transition-colors"
                    >
                      Inspect in Live Inspector
                    </button>
                    <button
                      type="button"
                      onClick={() => { window.open(fullDashboardUrl(msg.verification!.request_id), '_blank'); setOpenMenuId(null); }}
                      className="w-full text-left px-4 py-2 text-xs text-[#0C0C12] hover:bg-[#F6F5F1] transition-colors border-t border-[#F1EFEA]"
                    >
                      Inspect in Full Hearsay Dashboard
                    </button>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Auto-correct tag + diff toggle */}
          {msg.autoCorrectTag && (
            <div className="mt-2 flex items-center gap-2 flex-wrap">
              <span className="px-2 py-0.5 bg-[#E8F8D6] text-[#15803D] text-[10px] font-semibold rounded-full">
                Auto-Corrected via Hearsay Verification
              </span>
              <button
                type="button"
                onClick={e => {
                  e.stopPropagation();
                  onToggleOriginal(msg.id);
                }}
                className="text-[11px] text-[#65635C] underline hover:text-[#0C0C12]"
              >
                {msg.showOriginal ? 'Show Corrected' : 'Show Original'}
              </button>
            </div>
          )}
        </div>

        {/* Case A: Moderate contradiction — inline alert + regenerate button */}
        {msg.role === 'assistant' && isModerateContradiction && !msg.autoCorrectTag && !msg.isLoading && (
          <div className="flex items-center gap-3 px-1">
            <div className="flex-1 p-2.5 bg-[#FFFBEB] border border-[#FDE68A] rounded-xl text-[11px] text-[#92400E]">
              Potential ungrounded claim detected (Score: {pct.toFixed(0)}%). Some claims may not be supported by the source document.
            </div>
            <button
              type="button"
              onClick={() => onRegenerate()}
              className="px-3 py-2 bg-white border border-[#D9D4C7] rounded-xl text-[11px] text-[#0C0C12] font-medium hover:bg-[#F6F5F1] transition-colors shrink-0 whitespace-nowrap"
            >
              Regenerate with Strict Grounding
            </button>
          </div>
        )}

        {/* Case B: High contradiction — red auto-trigger banner */}
        {msg.role === 'assistant' && isHighContradiction && !msg.autoCorrectTag && !msg.isLoading && (
          <div className="px-1">
            <div className="p-2.5 bg-[#FEF2F2] border border-[#FECACA] rounded-xl text-[11px] text-[#991B1B]">
              High contradiction detected ({pct.toFixed(0)}%). Triggering automatic re-answer with strict context constraints...
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
