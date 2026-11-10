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

export interface BenchmarkTestCase {
  id: string;
  name: string;
  category: string;
  expectedVerdict: 'Verified' | 'Hallucination Detected';
  description: string;
  query: string;
  context: string;
  candidateResponse: string;
}

export const BENCHMARK_TEST_SUITE: BenchmarkTestCase[] = [
  {
    id: 'case-1-grounded',
    name: 'Case 1: Standard Grounded Prescribing',
    category: 'Faithful Baseline',
    expectedVerdict: 'Verified',
    description: 'Verifies model response that faithfully adheres to the clinical guideline without hallucination.',
    query: 'What is the recommended first-line therapy for mild community-acquired pneumonia in adult outpatients?',
    context: 'For mild outpatient community-acquired pneumonia in adult patients without significant comorbidities, Amoxicillin 500mg PO TID for 5 days is the recommended first-line antimicrobial regimen.',
    candidateResponse: 'For mild outpatient community-acquired pneumonia in adult patients without comorbidities, Amoxicillin 500mg PO TID for 5 days is the recommended first-line antimicrobial regimen.',
  },
  {
    id: 'case-2-dosage-contradiction',
    name: 'Case 2: Synthetic Dosage Contradiction',
    category: 'Parametric Contradiction',
    expectedVerdict: 'Hallucination Detected',
    description: 'Tests detector sensitivity when LLM parametric memory injects a contradictory dosage overriding the guideline.',
    query: 'What is the recommended dose of Ciprofloxacin for acute uncomplicated pyelonephritis?',
    context: 'Formulary Edition 2024 specifies Ciprofloxacin 500mg PO BID (1000mg total daily dose) for acute uncomplicated pyelonephritis.',
    candidateResponse: 'According to clinical protocols, Ciprofloxacin 1500mg once daily is recommended as the standard first-line therapy for acute uncomplicated pyelonephritis.',
  },
  {
    id: 'case-3-contraindication',
    name: 'Case 3: Unapproved Pediatric Contraindication',
    category: 'Clinical Safety Violation',
    expectedVerdict: 'Hallucination Detected',
    description: 'Evaluates detection of severe clinical contradictions where a contraindicated medication is falsely recommended.',
    query: 'Can Doxycycline be prescribed for pharyngitis in pediatric patients under 8 years of age?',
    context: 'Tetracyclines including doxycycline are strictly contraindicated in pediatric patients under 8 years of age due to risk of permanent tooth enamel discoloration and bone growth inhibition.',
    candidateResponse: 'Doxycycline is considered a safe, acceptable, and effective first-line therapy for young pediatric patients with acute pharyngitis.',
  },
  {
    id: 'case-4-ragtruth-timeline',
    name: 'Case 4: RAGTruth Historical Entailment Standard',
    category: 'Authentic Benchmark Corpus',
    expectedVerdict: 'Verified',
    description: 'Gold-standard benchmark pair from the ACL 2024 RAGTruth corpus testing strict temporal entailment.',
    query: 'What were the findings of the Anne Frank House research regarding Bergen-Belsen?',
    context: 'Witnesses suggest that Anne and Margot Frank had symptoms of typhus before February 7, 1945, in the Bergen-Belsen concentration camp.',
    candidateResponse: 'Witnesses suggest that Anne and Margot Frank showed symptoms of typhus before February 7, 1945, in the Bergen-Belsen concentration camp.',
  },
];

const BENCHMARK_DOCUMENTS = [
  {
    id: 'antimicrobial-guideline',
    label: 'Antimicrobial Guideline',
    description: 'Synthetic prescribing guidance for numerical fidelity and clinical-safety checks.',
    cases: BENCHMARK_TEST_SUITE.filter(testCase => testCase.id !== 'case-4-ragtruth-timeline'),
  },
  {
    id: 'ragtruth-archive',
    label: 'RAGTruth Historical Archive',
    description: 'An authentic benchmark sample for timeline entailment verification.',
    cases: BENCHMARK_TEST_SUITE.filter(testCase => testCase.id === 'case-4-ragtruth-timeline'),
  },
];

interface MinimalRAGViewProps {
  conversation: Conversation;
  onUpdate: (conv: Conversation) => void;
  onNewVerification: (v: VerificationResult | null, version?: 'original' | 'regenerated' | null) => void;
  onInspectMessage: (v: VerificationResult | null, version?: 'original' | 'regenerated' | null) => void;
  apiBase: string;
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
  const [isUploading, setIsUploading] = useState(false);
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
  const conversationRef = useRef(conversation);

  const toggleAdversarialMode = () => {
    const nextAdversarialState = !isAdversarial;
    setIsAdversarial(nextAdversarialState);
    setShowAdversarialTray(nextAdversarialState);
  };

  useEffect(() => {
    conversationRef.current = conversation;
  }, [conversation]);

  // Sync messages when conversation switches
  useEffect(() => {
    setMessages(conversation.messages);
    setInspectedMsgId(null);
  }, [conversation.id]);

  // Persist messages to conversation store whenever they change
  useEffect(() => {
    const firstPrompt = messages.find(message => message.role === 'user')?.content;
    onUpdate({
      ...conversationRef.current,
      messages,
      title: firstPrompt ? firstPrompt.split(/\s+/).slice(0, 5).join(' ') : conversationRef.current.title,
    });
  }, [messages]);

  // Fetch adversarial bank once
  useEffect(() => {
    fetch(`${apiBase}/v1/rag/adversarial-bank`)
      .then(r => r.ok ? r.json() : [])
      .then(setAdversarialBank)
      .catch(() => {});
  }, [apiBase]);

  // Reset context when entering live mode without an uploaded file
  useEffect(() => {
    if (mode === 'live' && !uploadedFilename) {
      setActiveContext('');
      setActiveSourceId('');
    }
  }, [mode, uploadedFilename]);

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
    setIsUploading(true);
    setErrorMsg(null);
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
      setErrorMsg('Could not upload PDF — ensure Hearsay Gateway is running on port 8000.');
    } finally {
      setIsUploading(false);
    }
  };

  const handleSend = async (overrideQuery?: string) => {
    const query = (overrideQuery ?? inputQuery).trim();
    if (!query || isSending) return;
    const isGreeting = /^(hi|hello|hey|good morning|good afternoon|good evening)[!?. ]*$/i.test(query);
    if (!isGreeting && !activeSourceId && !activeContext.trim()) {
      setErrorMsg('No reference document is loaded. Upload the guideline before requesting a grounded answer.');
      return;
    }
    setInputQuery('');
    setShowAdversarialTray(false);
    setErrorMsg(null);
    setIsSending(true);

    const userMsgId = `user-${Date.now()}`;
    const asstMsgId = `asst-${Date.now() + 1}`;
    const ts = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    const userMsg: RAGChatMessage = {
      id: userMsgId, role: 'user', content: query, timestamp: ts,
      telemetry: null, activeVersion: 'original',
    };
    const placeholderAsst: RAGChatMessage = {
      id: asstMsgId,
      role: 'assistant',
      content: '',
      timestamp: ts,
      telemetry: null,
      activeVersion: 'original',
      isLoading: true,
    };

    updateMessages(prev => {
      return [...prev, userMsg, placeholderAsst];
    });

    try {
      const payload: Record<string, any> = {
        model: 'gemini-3.5-flash-lite',
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
            ? {
                ...m,
                content,
                originalContent: content,
                telemetry: verification,
                originalTelemetry: verification,
                activeVersion: 'original',
                isLoading: false,
              }
            : m
        )
      );

      setInspectedMsgId(asstMsgId);
      onNewVerification(verification, 'original');
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
    originalVerification: VerificationResult,
  ) => {
    const contradictedClaims = originalVerification.claims
      .filter(c => c.status.toLowerCase().includes('contradiction') || c.status.toLowerCase().includes('contradict'))
      .map(c => `"${c.claim_text}"`)
      .join('; ');

    const augmentedPrompt = `Your previous answer contained claims not supported by the source document: ${contradictedClaims || 'see verification details'}. Recheck the source context and answer strictly based on it. Original question: ${originalQuery}`;

    try {
      const payload: Record<string, any> = {
        model: 'gemini-3.5-flash-lite',
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
      const regeneratedContent: string = data.choices?.[0]?.message?.content || '';
      const newVerification: VerificationResult | null = data.hearsay_verification ?? null;

      updateMessages(prev =>
        prev.map(m =>
          m.id === originalMsgId
            ? {
                ...m,
                regeneratedContent,
                regeneratedTelemetry: newVerification,
                content: regeneratedContent || m.content,
                telemetry: newVerification ?? m.telemetry,
                activeVersion: 'regenerated',
                autoCorrected: false,
                isAutoCorrecting: false,
              }
            : m
        )
      );

      if (newVerification) {
        setInspectedMsgId(originalMsgId);
        onNewVerification(newVerification, 'regenerated');
      }
    } catch {
      // Silent — original response is still shown
    }
  };

  const handleManualRegenerate = (msg: RAGChatMessage) => {
    if (!msg.telemetry) return;
    const messageIndex = messages.findIndex(item => item.id === msg.id);
    const originalQuery = messages.slice(0, messageIndex).reverse().find(item => item.role === 'user')?.content ?? '';
    triggerRegenerate(msg.id, originalQuery, msg.telemetry);
  };

  const handleInspectBubble = (msg: RAGChatMessage) => {
    if (msg.role !== 'assistant') return;
    setInspectedMsgId(msg.id);
    onInspectMessage(msg.telemetry ?? null, msg.activeVersion);
  };

  const handleSelectVersion = useCallback((msgId: string, version: 'original' | 'regenerated') => {
    const message = messages.find(m => m.id === msgId);
    const content = version === 'original' ? message?.originalContent : message?.regeneratedContent;
    const telemetry = version === 'original' ? message?.originalTelemetry : message?.regeneratedTelemetry;
    if (!message || !content) return;
    updateMessages(prev => prev.map(m => m.id === msgId ? {
      ...m, content, telemetry: telemetry ?? null, activeVersion: version,
    } : m));
    setInspectedMsgId(msgId);
    onInspectMessage(telemetry ?? null, version);
  }, [messages, onInspectMessage, updateMessages]);

  const fullDashboardUrl = (requestId: string) => {
    return `/?trace=${encodeURIComponent(requestId)}&view=dashboard`;
  };

  return (
    <div className="flex-1 flex flex-col overflow-hidden bg-[#FAFAF8]">
      {/* Source / Mode Bar */}
      <div className="border-b border-[#D9D4C7]/70 bg-[#FAF8F3] px-5 py-2.5 flex items-center gap-3 flex-wrap shrink-0">
        {mode === 'live' && (
          <>
            {isUploading ? (
              <div className="flex items-center gap-2 px-3 py-1 bg-white border border-[#D9D4C7] rounded-full text-xs text-[#0C0C12] font-medium shadow-sm">
                <svg className="w-3.5 h-3.5 animate-spin text-[#0C0C12]" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                  <path d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
                <span>Extracting PDF text...</span>
              </div>
            ) : uploadedFilename ? (
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
                  title="Remove uploaded document"
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
                className="flex items-center gap-1.5 px-3 py-1 bg-white border border-[#D9D4C7] rounded-full text-xs text-[#65635C] hover:text-[#0C0C12] hover:border-[#0C0C12] transition-colors shadow-sm"
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
          </>
        )}

        {mode === 'corpus' && (
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-[#D97706]" />
            <span className="text-xs font-semibold text-[#0C0C12]">Synthetic Counterfactual Test Suite</span>
            <span className="text-[10px] text-[#7A7870] font-mono px-2 py-0.5 bg-[#E8E4DA]/60 rounded-full">DeBERTa-v3 NLI</span>
          </div>
        )}

        {/* Mode Toggle */}
        <div className="inline-flex p-0.5 bg-[#E8E4DA]/60 border border-[#D9D4C7]/70 rounded-full ml-auto">
          {(['live', 'corpus'] as const).map(m => (
            <button
              key={m}
              type="button"
              onClick={() => setMode(m)}
              className={`px-3 py-1 rounded-full text-[11px] font-medium transition-colors ${
                mode === m ? 'bg-white text-[#0C0C12] shadow-sm font-semibold' : 'text-[#65635C] hover:text-[#0C0C12]'
              }`}
            >
              {m === 'live' ? 'Live Model' : 'Benchmark'}
            </button>
          ))}
        </div>
      </div>

      {/* Error Banner */}
      {errorMsg && (
        <div className="mx-5 mt-3 p-3 bg-[#FFF1F2] border border-[#FECDD3] rounded-xl text-xs text-[#DC2626] flex items-center justify-between shrink-0">
          <span>{errorMsg}</span>
          <button type="button" onClick={() => setErrorMsg(null)} className="ml-3 font-semibold hover:underline text-xs">Dismiss</button>
        </div>
      )}

      {/* Main Body: Live Chat OR Benchmark Suite */}
      {mode === 'corpus' ? (
        <BenchmarkSuiteView
          apiBase={apiBase}
          onNewVerification={onNewVerification}
          onSwitchToLive={() => setMode('live')}
        />
      ) : (
        <>
          {/* Conversational Live Thread */}
          <div ref={threadRef} className="flex-1 overflow-y-auto px-5 py-6 space-y-5 min-h-0">
            {messages.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center text-center space-y-3 text-[#9A9890]">
                <div className="w-12 h-12 rounded-full bg-[#E8E4DA]/50 flex items-center justify-center">
                  <svg className="w-5 h-5 text-[#7A7870]" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="1.8" viewBox="0 0 24 24">
                    <path d="M21 11.5a8.38 8.38 0 01-.9 3.8 8.5 8.5 0 01-7.6 4.7 8.38 8.38 0 01-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 01-.9-3.8 8.5 8.5 0 014.7-7.6 8.38 8.38 0 013.8-.9h.5a8.48 8.48 0 018 8v.5z" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </div>
                <p className="text-sm font-medium text-[#4A4842]">Start a conversation</p>
                <p className="text-[12px] max-w-sm text-[#9A9890] leading-relaxed">
                  Upload a PDF above or pick an adversarial prompt below to see Hearsay verify claims and catch hallucinations in real time.
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
                  onSelectVersion={handleSelectVersion}
                  openMenuId={openMenuId}
                  setOpenMenuId={setOpenMenuId}
                  fullDashboardUrl={fullDashboardUrl}
                />
              ))
            )}
            <div ref={bottomRef} />
          </div>

          {/* Adversarial Tray */}
          {isAdversarial && showAdversarialTray && (
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

          {/* Input Bar */}
          <div className="border-t border-[#D9D4C7]/70 bg-[#FAF8F3] px-5 py-3 flex items-center gap-2.5 shrink-0">
            <button
              type="button"
              onClick={toggleAdversarialMode}
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
        </>
      )}
    </div>
  );
}

// ── Benchmark Suite View (Dedicated, Non-Chat UX) ──────────────────────────────

interface BenchmarkSuiteViewProps {
  apiBase: string;
  onNewVerification: (v: VerificationResult | null) => void;
  onSwitchToLive: () => void;
}

function BenchmarkSuiteView({ apiBase, onNewVerification, onSwitchToLive }: BenchmarkSuiteViewProps) {
  const [selectedDocumentId, setSelectedDocumentId] = useState<string>(BENCHMARK_DOCUMENTS[0].id);
  const [selectedCaseId, setSelectedCaseId] = useState<string>(BENCHMARK_DOCUMENTS[0].cases[0].id);
  const [results, setResults] = useState<Record<string, VerificationResult>>({});
  const [isRunning, setIsRunning] = useState<boolean>(false);
  const [runningCaseId, setRunningCaseId] = useState<string | null>(null);

  const activeDocument = BENCHMARK_DOCUMENTS.find(document => document.id === selectedDocumentId) ?? BENCHMARK_DOCUMENTS[0];
  const activeCase = activeDocument.cases.find(c => c.id === selectedCaseId) ?? activeDocument.cases[0];

  const runTestCase = async (testCase: BenchmarkTestCase) => {
    setIsRunning(true);
    setRunningCaseId(testCase.id);
    try {
      const res = await fetch(`${apiBase}/verify`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          response_text: testCase.candidateResponse,
          verirag_context: {
            source_id: testCase.id,
            source_info: testCase.context,
          },
        }),
      });
      if (res.ok) {
        const data: VerificationResult = await res.json();
        setResults(prev => ({ ...prev, [testCase.id]: data }));
        onNewVerification(data);
      }
    } catch (err) {
      console.error('Benchmark test case failed:', err);
    } finally {
      setIsRunning(false);
      setRunningCaseId(null);
    }
  };

  const runAllCases = async () => {
    setIsRunning(true);
    for (const testCase of activeDocument.cases) {
      setRunningCaseId(testCase.id);
      try {
        const res = await fetch(`${apiBase}/verify`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            response_text: testCase.candidateResponse,
            verirag_context: {
              source_id: testCase.id,
              source_info: testCase.context,
            },
          }),
        });
        if (res.ok) {
          const data: VerificationResult = await res.json();
          setResults(prev => ({ ...prev, [testCase.id]: data }));
          onNewVerification(data);
        }
      } catch (err) {
        console.error('Benchmark runner failed on', testCase.id, err);
      }
    }
    setIsRunning(false);
    setRunningCaseId(null);
  };

  const activeResult = results[activeCase.id];

  const resetCases = () => {
    setResults({});
    setRunningCaseId(null);
    onNewVerification(null);
  };

  return (
    <div className="flex-1 overflow-y-auto p-5 md:p-6 space-y-5 min-h-0">
      {/* Explanatory Intent Banner */}
      <div className="p-4 bg-[#F5F2EB] border border-[#E2DFD7] rounded-2xl space-y-1.5 shadow-sm">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-[#D97706]" />
            <h3 className="font-serif text-sm font-semibold text-[#0C0C12]">
              Synthetic Counterfactual Benchmark Suite
            </h3>
          </div>
          <span className="text-[10px] text-[#7A7870] font-mono px-2 py-0.5 bg-white rounded-full border border-[#D9D4C7]">
            Deterministic NLI
          </span>
        </div>
        <p className="text-xs text-[#55534D] leading-relaxed">
          Benchmark mode is a dedicated synthetic test suite for evaluating detector accuracy, not a casual chat. Select a reference document and run its controlled cases to inspect groundedness, claim attribution, and latency without live API keys.
        </p>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-[#D9D4C7] bg-white p-3">
        <label className="flex items-center gap-2 text-xs font-medium text-[#4A4842]">
          Reference document
          <select
            value={selectedDocumentId}
            onChange={event => {
              const nextDocument = BENCHMARK_DOCUMENTS.find(document => document.id === event.target.value) ?? BENCHMARK_DOCUMENTS[0];
              setSelectedDocumentId(nextDocument.id);
              setSelectedCaseId(nextDocument.cases[0].id);
              onNewVerification(null);
            }}
            className="rounded-lg border border-[#D9D4C7] bg-[#FAF8F3] px-2.5 py-1.5 text-xs text-[#0C0C12] focus:outline-none focus:ring-2 focus:ring-[#0C0C12]/10"
          >
            {BENCHMARK_DOCUMENTS.map(document => <option key={document.id} value={document.id}>{document.label}</option>)}
          </select>
        </label>
        <button type="button" onClick={resetCases} disabled={isRunning} className="rounded-lg border border-[#D9D4C7] px-3 py-1.5 text-xs font-medium text-[#4A4842] hover:bg-[#F6F5F1] disabled:opacity-40">
          Reset Test Cases
        </button>
      </div>

      {/* Test Case Selector Tabs */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2.5">
        {activeDocument.cases.map(tc => {
          const hasResult = results[tc.id];
          const isSelected = tc.id === activeCase.id;
          return (
            <button
              key={tc.id}
              type="button"
              onClick={() => {
                setSelectedCaseId(tc.id);
                if (hasResult) onNewVerification(hasResult);
              }}
              className={`p-3 rounded-xl border text-left transition-all duration-150 ${
                isSelected
                  ? 'bg-white border-[#0C0C12] shadow-sm ring-1 ring-[#0C0C12]/10'
                  : 'bg-white/70 border-[#D9D4C7] hover:bg-white hover:border-[#0C0C12]/30'
              }`}
            >
              <div className="flex items-center justify-between text-[10px] font-semibold text-[#7A7870] mb-1">
                <span>{tc.category}</span>
                {hasResult && (
                  <span className={`w-1.5 h-1.5 rounded-full ${
                    hasResult.overall_status === 'Verified' ? 'bg-[#15803D]' : 'bg-[#DC2626]'
                  }`} />
                )}
              </div>
              <p className="text-xs font-semibold text-[#0C0C12] truncate">{tc.name}</p>
              <p className="text-[11px] text-[#9A9890] mt-1 line-clamp-2 leading-snug">
                {tc.description}
              </p>
            </button>
          );
        })}
      </div>

      {/* Active Test Case Detail Card */}
      <div className="bg-white border border-[#D9D4C7] rounded-2xl p-5 space-y-4 shadow-sm">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-[#F1EFEA]">
          <div>
            <h4 className="font-serif text-base font-semibold text-[#0C0C12]">{activeCase.name}</h4>
            <p className="text-xs text-[#7A7870] mt-0.5">{activeCase.description}</p>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => runTestCase(activeCase)}
              disabled={isRunning}
              className="px-4 py-2 bg-[#0C0C12] hover:bg-black text-white text-xs font-medium rounded-xl transition-all duration-150 enabled:active:scale-95 disabled:opacity-40 flex items-center gap-2"
            >
              {runningCaseId === activeCase.id ? (
                <>
                  <svg className="w-3.5 h-3.5 animate-spin" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                    <path d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                  <span>Running DeBERTa...</span>
                </>
              ) : (
                <span>Run Test Case</span>
              )}
            </button>
            <button
              type="button"
              onClick={runAllCases}
              disabled={isRunning}
              className="px-3.5 py-2 bg-white hover:bg-[#F6F5F1] border border-[#D9D4C7] text-xs font-medium text-[#0C0C12] rounded-xl transition-colors"
            >
              Run All {activeDocument.cases.length} Cases
            </button>
          </div>
        </div>

        <div className="rounded-xl border border-[#E8E4DA] bg-[#FAF8F3] px-3 py-2 text-xs text-[#4A4842]">
          <span className="font-semibold text-[#0C0C12]">Objective: </span>{activeCase.description}
        </div>

        {/* Clinical Question */}
        <div className="space-y-1">
          <span className="text-[10px] font-semibold text-[#9A9890] uppercase tracking-wider block">
            Target Clinical Prompt
          </span>
          <p className="text-xs font-medium text-[#0C0C12] bg-[#FAF8F3] p-2.5 rounded-xl border border-[#E8E4DA]">
            {activeCase.query}
          </p>
        </div>

        {/* Source Context vs Candidate Response */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="space-y-1">
            <span className="text-[10px] font-semibold text-[#9A9890] uppercase tracking-wider block">
              Reference Document Context
            </span>
            <div className="p-3 bg-[#FAF8F3] rounded-xl border border-[#E8E4DA] text-xs text-[#4A4842] leading-relaxed font-serif italic min-h-[90px]">
              &ldquo;{activeCase.context}&rdquo;
            </div>
          </div>
          <div className="space-y-1">
            <span className="text-[10px] font-semibold text-[#9A9890] uppercase tracking-wider block">
              Candidate Model Assertion
            </span>
            <div className="p-3 bg-white rounded-xl border border-[#D9D4C7] text-xs text-[#0C0C12] leading-relaxed min-h-[90px]">
              {activeCase.candidateResponse}
            </div>
          </div>
        </div>

        {/* Telemetry Results (if run) */}
        {activeResult ? (
          <div className="mt-4 pt-4 border-t border-[#F1EFEA] space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-center gap-3">
                <span className={`px-3 py-1 rounded-full text-xs font-semibold ${
                  activeResult.overall_status === 'Verified'
                    ? 'bg-[#E8F8D6] text-[#15803D]'
                    : 'bg-[#FFF1F2] text-[#DC2626]'
                }`}>
                  {activeResult.overall_status === 'Verified' ? 'Grounded (Verified)' : 'Contradiction Flagged'}
                </span>
                <span className="text-xs font-medium text-[#4A4842]">
                  Score: <strong className="font-mono text-[#0C0C12]">{activeResult.groundedness_score}%</strong>
                </span>
                <span className="text-xs text-[#7A7870] font-mono">
                  Latency: {activeResult.latency_ms.toFixed(1)} ms
                </span>
              </div>
              <button
                type="button"
                onClick={() => onNewVerification(activeResult)}
                className="text-xs font-medium text-[#0C0C12] hover:underline"
              >
                Inspect in Live Drawer →
              </button>
            </div>

            {/* Claims Breakdown */}
            <div className="space-y-2">
              <span className="text-[10px] font-semibold text-[#9A9890] uppercase tracking-wider block">
                Sentence-Level Claim Deconstruction ({activeResult.claims.length} claims)
              </span>
              <div className="space-y-2">
                {activeResult.claims.map((claim, idx) => {
                  const isSupported = claim.status.toLowerCase().includes('supported') && !claim.status.toLowerCase().includes('unsupported');
                  return (
                    <div key={idx} className="p-3 rounded-xl border border-[#E8E4DA] bg-[#FAF8F3] text-xs space-y-1.5">
                      <div className="flex items-center justify-between">
                        <span className="font-medium text-[#0C0C12]">&ldquo;{claim.claim_text}&rdquo;</span>
                        <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${
                          isSupported ? 'bg-[#E8F8D6] text-[#15803D]' : 'bg-[#FEE2E2] text-[#991B1B]'
                        }`}>
                          {claim.status}
                        </span>
                      </div>
                      {claim.nli_logits && (
                        <div className="flex items-center gap-4 text-[10px] font-mono text-[#7A7870] pt-1 border-t border-[#F1EFEA]">
                          <span>Entailment: {(claim.nli_logits.entailment * 100).toFixed(1)}%</span>
                          <span>Contradiction: {(claim.nli_logits.contradiction * 100).toFixed(1)}%</span>
                          <span>Neutral: {(claim.nli_logits.neutral * 100).toFixed(1)}%</span>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        ) : (
          <div className="mt-3 p-3 bg-[#FAF8F3] rounded-xl border border-dashed border-[#D9D4C7] text-center text-xs text-[#9A9890]">
            Click &ldquo;Run Test Case&rdquo; to execute DeBERTa-v3 cross-encoder evaluation against this synthetic pair.
          </div>
        )}
      </div>

      {/* Bottom Switch to Live Bar */}
      <div className="p-3.5 bg-white border border-[#D9D4C7] rounded-xl flex items-center justify-between text-xs">
        <span className="text-[#65635C]">
          Benchmark suite is active. Want to chat with live LLMs or test your own uploaded PDF?
        </span>
        <button
          type="button"
          onClick={onSwitchToLive}
          className="font-semibold text-[#0C0C12] hover:underline shrink-0 ml-3"
        >
          Switch to Live Model →
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
  onSelectVersion: (msgId: string, version: 'original' | 'regenerated') => void;
  openMenuId: string | null;
  setOpenMenuId: (id: string | null) => void;
  fullDashboardUrl: (requestId: string) => string;
}

function MessageBubble({ msg, isInspected, onInspect, onRegenerate, onSelectVersion, openMenuId, setOpenMenuId, fullDashboardUrl }: BubbleProps) {
  const telemetry = msg.telemetry;
  const pct = telemetry ? (telemetry.total_claims > 0 ? (telemetry.contradicted_claims / telemetry.total_claims) * 100 : 0) : 0;
  const isHighContradiction = pct > 30;
  const isModerateContradiction = pct > 0 && pct <= 30;
  const versionName = msg.activeVersion === 'original' ? 'Original answer' : 'Regenerated answer';
  const versionScore = (result: VerificationResult | null | undefined) => {
    if (!result) return 'not verified';
    const contradiction = result.total_claims ? (result.contradicted_claims / result.total_claims) * 100 : 0;
    return contradiction > 0 ? `${contradiction.toFixed(0)}% contradiction` : `${result.groundedness_score}% grounded`;
  };

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
            <p className="whitespace-pre-wrap select-text">{msg.content}</p>
          )}

          {/* Verification status line */}
          {msg.role === 'assistant' && !msg.isLoading && (
            <div className="mt-3 pt-2.5 border-t border-[#F1EFEA] flex items-center justify-between gap-3">
              {telemetry ? (
                <div className="flex items-center gap-1.5">
                  <span className={`w-1.5 h-1.5 rounded-full ${isHighContradiction ? 'bg-[#DC2626]' : isModerateContradiction ? 'bg-[#D97706]' : 'bg-[#15803D]'}`} />
                  <span className={`text-[11px] font-medium ${isHighContradiction ? 'text-[#DC2626]' : isModerateContradiction ? 'text-[#D97706]' : 'text-[#15803D]'}`}>
                    {versionName} · {isHighContradiction ? `${pct.toFixed(0)}% contradiction` : isModerateContradiction ? `${pct.toFixed(0)}% potential conflict` : `${telemetry.groundedness_score}% grounded`}
                  </span>
                  <span className="text-[10px] text-[#9A9890] font-mono">
                    ({telemetry.supported_claims}/{telemetry.total_claims})
                  </span>
                </div>
              ) : <span className="text-[11px] text-[#9A9890]">Not verified — no reference document</span>}

              {/* 3-dot menu */}
              <div className="relative" onClick={e => e.stopPropagation()}>
                <button
                  type="button"
                  onClick={() => setOpenMenuId(openMenuId === msg.id ? null : msg.id)}
                  className="p-1 rounded-lg text-[#9A9890] hover:text-[#0C0C12] hover:bg-[#F1EFEA] transition-colors"
                  title="Message options"
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
                    {telemetry ? (
                      <button
                        type="button"
                        onClick={() => { window.open(fullDashboardUrl(telemetry.request_id), '_blank'); setOpenMenuId(null); }}
                        className="w-full text-left px-4 py-2 text-xs text-[#0C0C12] hover:bg-[#F6F5F1] transition-colors border-t border-[#F1EFEA]"
                      >
                        Inspect in Full Hearsay Dashboard
                      </button>
                    ) : <p className="border-t border-[#F1EFEA] px-4 py-2 text-[11px] text-[#9A9890]">No audit trace was created.</p>}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Auto-correct tag + diff toggle */}
          {msg.regeneratedContent && (
            <div className="mt-2 flex items-center gap-2 flex-wrap">
              <button
                type="button"
                onClick={e => {
                  e.stopPropagation();
                  onSelectVersion(msg.id, 'original');
                }}
                className={`px-2 py-0.5 rounded-full text-[10px] font-semibold transition-colors ${msg.activeVersion === 'original' ? 'bg-[#0C0C12] text-white' : 'bg-[#F1EFEA] text-[#65635C] hover:text-[#0C0C12]'}`}
              >
                Original · {versionScore(msg.originalTelemetry)}
              </button>
              <button
                type="button"
                onClick={e => {
                  e.stopPropagation();
                  onSelectVersion(msg.id, 'regenerated');
                }}
                className={`px-2 py-0.5 rounded-full text-[10px] font-semibold transition-colors ${msg.activeVersion === 'regenerated' ? 'bg-[#0C0C12] text-white' : 'bg-[#F1EFEA] text-[#65635C] hover:text-[#0C0C12]'}`}
              >
                Regenerated · {versionScore(msg.regeneratedTelemetry)}
              </button>
            </div>
          )}
        </div>

        {/* Case A: Moderate contradiction — inline alert + regenerate button */}
        {msg.role === 'assistant' && isModerateContradiction && !msg.regeneratedContent && !msg.isLoading && (
          <div className="flex items-center gap-3 px-1">
            <div className="flex-1 p-2.5 bg-[#FFFBEB] border border-[#FDE68A] rounded-xl text-[11px] text-[#92400E]">
              Potential ungrounded claim detected (Score: {pct.toFixed(0)}%). Some claims may not be supported by the source document.
            </div>
            <button
              type="button"
              onClick={onRegenerate}
              className="px-3 py-1.5 bg-[#0C0C12] text-white rounded-lg text-xs font-medium hover:bg-black transition-colors shrink-0 shadow-sm"
            >
              Regenerate with Grounded Context
            </button>
          </div>
        )}

        {/* Case B: High contradiction — red auto-trigger banner */}
        {msg.role === 'assistant' && isHighContradiction && !msg.regeneratedContent && !msg.isLoading && (
          <div className="flex flex-wrap items-center justify-between gap-3 p-3 bg-[#FFF1F2] border border-[#FECDD3] rounded-xl text-[11px] text-[#991B1B] mx-1" role="alert">
            <div>
              <p className="font-semibold">High contradiction detected in the original answer ({pct.toFixed(0)}%).</p>
              <p className="mt-0.5 text-[#B42318]">Hearsay kept this answer unchanged. Review its evidence, then regenerate only if you want a grounded revision.</p>
            </div>
            <button
              type="button"
              onClick={onRegenerate}
              className="shrink-0 rounded-lg bg-[#0C0C12] px-3 py-1.5 text-xs font-semibold text-white hover:bg-black transition-colors"
            >
              Regenerate with Grounded Context
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
