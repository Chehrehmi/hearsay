import { useState, useEffect } from 'react';
import type { VerificationResult } from './types';
import { MinimalRAGView } from './components/MinimalRAGView';
import { HearsayDrawer } from './components/HearsayDrawer';
import { ConversationSidebar } from './components/ConversationSidebar';
import { SettingsModal } from './components/SettingsModal';
import {
  createConversation,
  listConversations,
  saveConversation,
  type Conversation,
} from './lib/conversationStore';

export function App() {
  const apiBase =
    typeof window !== 'undefined' && window.location.port === '5173'
      ? 'http://localhost:8000'
      : '';

  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<string>('');
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [drawerVerification, setDrawerVerification] = useState<VerificationResult | null>(null);
  const [isOnline, setIsOnline] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);

  // Initialise: load or create first conversation
  useEffect(() => {
    const existing = listConversations();
    if (existing.length > 0) {
      setConversations(existing);
      setActiveConversationId(existing[0].id);
    } else {
      const conv = createConversation();
      setConversations([conv]);
      setActiveConversationId(conv.id);
    }
  }, []);

  // Gateway health poll
  useEffect(() => {
    const check = async () => {
      try {
        const r = await fetch(`${apiBase}/health`);
        setIsOnline(r.ok);
      } catch {
        setIsOnline(false);
      }
    };
    check();
    const id = setInterval(check, 10_000);
    return () => clearInterval(id);
  }, [apiBase]);

  const handleNewConversation = () => {
    const conv = createConversation();
    setConversations(listConversations());
    setActiveConversationId(conv.id);
    setDrawerVerification(null);
    setDrawerOpen(false);
  };

  const handleSelectConversation = (id: string) => {
    setActiveConversationId(id);
    setDrawerVerification(null);
    setDrawerOpen(false);
  };

  const handleUpdateConversation = (conv: Conversation) => {
    saveConversation(conv);
    setConversations(listConversations());
  };

  const handleNewVerification = (v: VerificationResult | null) => {
    setDrawerVerification(v);
    if (v) setDrawerOpen(true);
  };

  const activeConversation =
    conversations.find(c => c.id === activeConversationId) ?? null;

  return (
    <div className="min-h-screen bg-[#F5F3EE] flex flex-col font-sans">
      {/* Header */}
      <header className="h-14 border-b border-[#D9D4C7]/70 bg-[#FAF8F3] flex items-center px-5 shrink-0 gap-4">
        {/* Wordmark */}
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
          <span className="font-serif text-[18px] font-semibold tracking-tight text-[#0C0C12]">
            Hearsay
          </span>
          <span className="text-[11px] text-[#9A9890] font-medium hidden sm:inline">
            RAG Verification
          </span>
        </div>

        <div className="flex-1" />

        {/* Gateway status */}
        <div className="flex items-center gap-1.5 text-xs text-[#65635C]">
          <span className={`w-1.5 h-1.5 rounded-full ${isOnline ? 'bg-[#15803D]' : 'bg-[#DC2626]'}`} />
          <span className="hidden sm:inline">{isOnline ? 'Gateway live' : 'Gateway offline'}</span>
        </div>

        {/* Settings button */}
        <button
          type="button"
          onClick={() => setSettingsOpen(true)}
          className="p-2 rounded-lg text-[#65635C] hover:text-[#0C0C12] hover:bg-[#E8E4DA]/60 transition-colors"
          title="API Key Settings"
        >
          <svg width="16" height="16" fill="none" stroke="currentColor" strokeWidth="1.8" viewBox="0 0 24 24">
            <path d="M12 15a3 3 0 100-6 3 3 0 000 6z" strokeLinecap="round" strokeLinejoin="round" />
            <path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 012.83-2.83l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </button>
      </header>

      {/* Body: 3-panel layout */}
      <div className="flex flex-1 overflow-hidden">
        <ConversationSidebar
          conversations={conversations}
          activeId={activeConversationId}
          onSelect={handleSelectConversation}
          onNew={handleNewConversation}
        />
        {activeConversation && (
          <MinimalRAGView
            conversation={activeConversation}
            onUpdate={handleUpdateConversation}
            onNewVerification={handleNewVerification}
            onInspectMessage={setDrawerVerification}
            apiBase={apiBase}
          />
        )}
        <HearsayDrawer
          verification={drawerVerification}
          open={drawerOpen}
          onClose={() => setDrawerOpen(false)}
          apiBase={apiBase}
        />
      </div>

      {settingsOpen && (
        <SettingsModal apiBase={apiBase} onClose={() => setSettingsOpen(false)} />
      )}
    </div>
  );
}

export default App;
