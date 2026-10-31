import type { Conversation } from '../lib/conversationStore';
import { groupConversationsByDate } from '../lib/conversationStore';

interface ConversationSidebarProps {
  conversations: Conversation[];
  activeId: string;
  isOpen?: boolean;
  onSelect: (id: string) => void;
  onNew: () => void;
}

export function ConversationSidebar({
  conversations,
  activeId,
  isOpen = true,
  onSelect,
  onNew,
}: ConversationSidebarProps) {
  const groups = groupConversationsByDate(conversations);

  return (
    <aside
      className={`shrink-0 border-r border-[#D9D4C7]/70 bg-[#EDE9E0]/60 flex flex-col transition-all duration-200 ease-in-out overflow-hidden ${
        isOpen ? 'w-[220px] xl:w-[240px]' : 'w-0'
      }`}
    >
      {/* New conversation button */}
      <div className="p-3 border-b border-[#D9D4C7]/60">
        <button
          type="button"
          onClick={onNew}
          className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-sm font-medium text-[#0C0C12] bg-white border border-[#D9D4C7]/80 hover:bg-[#F6F5F1] transition-colors shadow-sm"
        >
          <svg width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
            <path d="M12 5v14M5 12h14" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          New Conversation
        </button>
      </div>

      {/* Conversation list */}
      <div className="flex-1 overflow-y-auto py-2">
        {groups.length === 0 && (
          <p className="text-[11px] text-[#9A9890] text-center px-4 pt-8">
            No conversations yet
          </p>
        )}
        {groups.map(group => (
          <div key={group.label} className="mb-2">
            <p className="text-[10px] font-semibold text-[#9A9890] uppercase tracking-wider px-4 py-1.5">
              {group.label}
            </p>
            {group.items.map(conv => (
              <button
                key={conv.id}
                type="button"
                onClick={() => onSelect(conv.id)}
                className={`w-full text-left px-4 py-2 text-[13px] truncate transition-colors ${
                  conv.id === activeId
                    ? 'bg-white text-[#0C0C12] font-medium border-l-2 border-[#0C0C12]'
                    : 'text-[#4A4842] hover:bg-white/60 border-l-2 border-transparent'
                }`}
                title={conv.title}
              >
                {conv.title}
              </button>
            ))}
          </div>
        ))}
      </div>
    </aside>
  );
}
