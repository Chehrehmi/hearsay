/**
 * conversationStore.ts
 *
 * Persists conversation history to localStorage.
 * Each conversation stores its full message array (including verification results),
 * so clicking a previous conversation replays the full verified chat thread.
 *
 * Storage key: 'hearsay_conversations'
 * Format: JSON array of Conversation, sorted newest-first on read.
 */

import type { RAGChatMessage } from '../types';

export interface Conversation {
  id: string;
  title: string;        // first user message, truncated to 40 chars
  createdAt: number;    // Date.now() timestamp
  updatedAt: number;
  messages: RAGChatMessage[];
}

const STORAGE_KEY = 'hearsay_conversations';

function readAll(): Conversation[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    return JSON.parse(raw) as Conversation[];
  } catch {
    return [];
  }
}

function writeAll(convs: Conversation[]): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(convs));
}

export function listConversations(): Conversation[] {
  return readAll().sort((a, b) => b.updatedAt - a.updatedAt);
}

export function getConversation(id: string): Conversation | null {
  return readAll().find(c => c.id === id) ?? null;
}

export function createConversation(): Conversation {
  const conv: Conversation = {
    id: `conv-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
    title: 'New Conversation',
    createdAt: Date.now(),
    updatedAt: Date.now(),
    messages: [],
  };
  const all = readAll();
  writeAll([conv, ...all]);
  return conv;
}

export function saveConversation(conv: Conversation): void {
  const all = readAll();
  const idx = all.findIndex(c => c.id === conv.id);
  const updated = { ...conv, updatedAt: Date.now() };
  if (idx >= 0) {
    all[idx] = updated;
  } else {
    all.unshift(updated);
  }
  writeAll(all);
}

export function deleteConversation(id: string): void {
  writeAll(readAll().filter(c => c.id !== id));
}

/** Groups conversations by recency label for sidebar display. */
export function groupConversationsByDate(convs: Conversation[]): { label: string; items: Conversation[] }[] {
  const now = Date.now();
  const ONE_DAY = 86_400_000;
  const groups: { label: string; items: Conversation[] }[] = [];

  const today = convs.filter(c => now - c.updatedAt < ONE_DAY);
  const yesterday = convs.filter(c => {
    const age = now - c.updatedAt;
    return age >= ONE_DAY && age < 2 * ONE_DAY;
  });
  const older = convs.filter(c => now - c.updatedAt >= 2 * ONE_DAY);

  if (today.length) groups.push({ label: 'Today', items: today });
  if (yesterday.length) groups.push({ label: 'Yesterday', items: yesterday });

  // Group remaining by date string
  const byDate: Record<string, Conversation[]> = {};
  for (const c of older) {
    const label = new Date(c.updatedAt).toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
    (byDate[label] ??= []).push(c);
  }
  for (const [label, items] of Object.entries(byDate)) {
    groups.push({ label, items });
  }

  return groups;
}
