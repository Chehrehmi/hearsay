import { useState, useEffect } from 'react';

type Provider = 'gemini' | 'openai' | 'groq' | 'custom';

interface ProviderConfig {
  label: string;
  placeholder: string;
  docs: string;
}

const PROVIDERS: Record<Provider, ProviderConfig> = {
  gemini: {
    label: 'Google Gemini',
    placeholder: 'AIza...',
    docs: 'https://aistudio.google.com/app/apikey',
  },
  openai: {
    label: 'OpenAI',
    placeholder: 'sk-...',
    docs: 'https://platform.openai.com/api-keys',
  },
  groq: {
    label: 'Groq',
    placeholder: 'gsk_...',
    docs: 'https://console.groq.com/keys',
  },
  custom: {
    label: 'Custom (OpenAI-compatible)',
    placeholder: 'API key for your endpoint',
    docs: '',
  },
};

interface SettingsStatus {
  gemini: boolean;
  openai: boolean;
  groq: boolean;
  custom: boolean;
}

interface SettingsModalProps {
  apiBase: string;
  onClose: () => void;
}

export function SettingsModal({ apiBase, onClose }: SettingsModalProps) {
  const [selectedProvider, setSelectedProvider] = useState<Provider>('gemini');
  const [apiKey, setApiKey] = useState('');
  const [baseUrl, setBaseUrl] = useState('');
  const [status, setStatus] = useState<SettingsStatus>({ gemini: false, openai: false, groq: false, custom: false });
  const [saveState, setSaveState] = useState<'idle' | 'saving' | 'saved' | 'error'>('idle');
  const [errorDetail, setErrorDetail] = useState('');
  const [isClearing, setIsClearing] = useState(false);

  // Load status on mount
  useEffect(() => {
    fetch(`${apiBase}/v1/settings/status`)
      .then(r => r.ok ? r.json() : {})
      .then((data: Partial<SettingsStatus>) => {
        setStatus({
          gemini: data.gemini ?? false,
          openai: data.openai ?? false,
          groq: data.groq ?? false,
          custom: data.custom ?? false,
        });
      })
      .catch(() => {});
  }, [apiBase]);

  // Clear key field when switching provider
  useEffect(() => {
    setApiKey('');
    setBaseUrl('');
    setSaveState('idle');
    setErrorDetail('');
  }, [selectedProvider]);

  const handleSave = async () => {
    const trimmed = apiKey.trim();
    if (!trimmed) return;
    setSaveState('saving');
    setErrorDetail('');
    try {
      const body: Record<string, string> = { provider: selectedProvider, api_key: trimmed };
      if (selectedProvider === 'custom' && baseUrl.trim()) {
        body.base_url = baseUrl.trim();
      }
      const r = await fetch(`${apiBase}/v1/settings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (!r.ok) {
        const err = await r.json().catch(() => ({}));
        throw new Error(err.detail || `Save failed (${r.status})`);
      }
      setSaveState('saved');
      setApiKey('');
      setStatus(prev => ({ ...prev, [selectedProvider]: true }));
      setTimeout(() => setSaveState('idle'), 2500);
    } catch (err: any) {
      setSaveState('error');
      setErrorDetail(err.message || 'Could not save key.');
    }
  };

  const handleClearKey = async () => {
    if (!window.confirm(`Are you sure you want to remove the saved API key for ${PROVIDERS[selectedProvider].label}?`)) {
      return;
    }
    setIsClearing(true);
    setErrorDetail('');
    try {
      const r = await fetch(`${apiBase}/v1/settings/${selectedProvider}`, {
        method: 'DELETE',
      });
      if (!r.ok) {
        throw new Error('Could not remove key.');
      }
      setStatus(prev => ({ ...prev, [selectedProvider]: false }));
      setApiKey('');
      setSaveState('idle');
    } catch (err: any) {
      setErrorDetail(err.message || 'Failed to remove key.');
    } finally {
      setIsClearing(false);
    }
  };

  const config = PROVIDERS[selectedProvider];

  return (
    // Backdrop
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-[#0C0C12]/40 backdrop-blur-[2px]"
      onClick={e => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div className="relative w-full max-w-md mx-4 bg-white rounded-2xl shadow-2xl border border-[#D9D4C7]/80 overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 pt-6 pb-4 border-b border-[#F1EFEA]">
          <div>
            <h2 className="text-sm font-semibold text-[#0C0C12]">API Key Settings</h2>
            <p className="text-[11px] text-[#9A9890] mt-0.5">
              Keys are stored server-side and never returned to the browser.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-lg text-[#9A9890] hover:text-[#0C0C12] hover:bg-[#F1EFEA] transition-colors"
          >
            <svg width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
              <path d="M18 6L6 18M6 6l12 12" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </button>
        </div>

        {/* Body */}
        <div className="px-6 py-5 space-y-5">
          {/* Provider selector */}
          <div className="space-y-1.5">
            <label className="text-[10px] font-semibold text-[#9A9890] uppercase tracking-wider block">
              Provider
            </label>
            <div className="grid grid-cols-2 gap-2">
              {(Object.keys(PROVIDERS) as Provider[]).map(p => {
                const isConfigured = status[p];
                return (
                  <button
                    key={p}
                    type="button"
                    onClick={() => setSelectedProvider(p)}
                    className={`px-3 py-2.5 rounded-xl border text-left transition-colors ${
                      selectedProvider === p
                        ? 'border-[#0C0C12] bg-[#0C0C12] text-white'
                        : 'border-[#D9D4C7] bg-white text-[#0C0C12] hover:border-[#0C0C12]/40 hover:bg-[#F6F5F1]'
                    }`}
                  >
                    <div className="text-[11px] font-medium">{PROVIDERS[p].label}</div>
                    <div className={`text-[10px] mt-0.5 ${
                      selectedProvider === p ? 'text-white/60' : isConfigured ? 'text-[#15803D]' : 'text-[#9A9890]'
                    }`}>
                      {isConfigured ? 'Configured' : 'Not set'}
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Custom base URL (only for custom provider) */}
          {selectedProvider === 'custom' && (
            <div className="space-y-1.5">
              <label className="text-[10px] font-semibold text-[#9A9890] uppercase tracking-wider block">
                Base URL
              </label>
              <input
                type="url"
                value={baseUrl}
                onChange={e => setBaseUrl(e.target.value)}
                placeholder="https://api.example.com/v1"
                className="w-full px-3.5 py-2.5 bg-[#FAF8F3] border border-[#D9D4C7] rounded-xl text-sm text-[#0C0C12] placeholder-[#B5B0A8] focus:outline-none focus:ring-2 focus:ring-[#0C0C12]/10 focus:border-[#0C0C12] transition-colors"
              />
            </div>
          )}

          {/* API key input */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <label className="text-[10px] font-semibold text-[#9A9890] uppercase tracking-wider block">
                API Key
              </label>
              {config.docs && (
                <a
                  href={config.docs}
                  target="_blank"
                  rel="noreferrer"
                  className="text-[10px] text-[#65635C] hover:text-[#0C0C12] underline transition-colors"
                >
                  Get key
                </a>
              )}
            </div>
            <input
              type="password"
              value={apiKey}
              onChange={e => setApiKey(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter' && apiKey.trim()) handleSave(); }}
              placeholder={
                status[selectedProvider]
                  ? 'Enter a new key to replace the saved one'
                  : config.placeholder
              }
              autoComplete="off"
              className="w-full px-3.5 py-2.5 bg-[#FAF8F3] border border-[#D9D4C7] rounded-xl text-sm text-[#0C0C12] placeholder-[#B5B0A8] focus:outline-none focus:ring-2 focus:ring-[#0C0C12]/10 focus:border-[#0C0C12] transition-colors font-mono"
            />
            {status[selectedProvider] && (
              <p className="text-[10px] text-[#15803D] flex items-center gap-1">
                <svg width="10" height="10" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
                  <path d="M20 6L9 17l-5-5" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
                A key is already saved for {PROVIDERS[selectedProvider].label}.
                Leave blank to keep existing.
              </p>
            )}
          </div>

          {/* Error message */}
          {saveState === 'error' && (
            <div className="p-3 bg-[#FFF1F2] border border-[#FECDD3] rounded-xl text-[11px] text-[#DC2626]">
              {errorDetail}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 pb-6 flex items-center gap-3">
          {status[selectedProvider] && (
            <button
              type="button"
              onClick={handleClearKey}
              disabled={isClearing}
              className="mr-auto px-3.5 py-2 rounded-xl border border-[#FECDD3] bg-[#FFF1F2] hover:bg-[#FFE4E6] text-xs font-medium text-[#DC2626] transition-colors"
            >
              {isClearing ? 'Clearing...' : 'Clear Key'}
            </button>
          )}
          <div className="flex items-center gap-2 ml-auto">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-xl border border-[#D9D4C7] text-xs font-medium text-[#65635C] hover:text-[#0C0C12] hover:border-[#0C0C12] transition-colors"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleSave}
              disabled={!apiKey.trim() || saveState === 'saving'}
              className="px-5 py-2 bg-[#0C0C12] hover:bg-black text-white text-xs font-medium rounded-xl transition-all duration-150 enabled:active:scale-95 disabled:opacity-40"
            >
              {saveState === 'saving' ? 'Saving...' : saveState === 'saved' ? 'Saved' : 'Save Key'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
