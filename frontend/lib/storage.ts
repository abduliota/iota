import { Chat } from './types';

const STORAGE_KEY = 'ksa_regtech_chats';

export function saveChat(chat: Chat): void {
  const chats = getChats();
  const existingIndex = chats.findIndex(c => c.id === chat.id);
  
  if (existingIndex >= 0) {
    chats[existingIndex] = chat;
  } else {
    chats.push(chat);
  }
  
  localStorage.setItem(STORAGE_KEY, JSON.stringify(chats));
}

export function getChats(): Chat[] {
  if (typeof window === 'undefined') return [];
  
  const stored = localStorage.getItem(STORAGE_KEY);
  if (!stored) return [];
  
  try {
    const chats = JSON.parse(stored);
    return chats.map((chat: any) => ({
      ...chat,
      createdAt: new Date(chat.createdAt),
      updatedAt: new Date(chat.updatedAt),
      messages: chat.messages.map((msg: any) => ({
        ...msg,
        timestamp: new Date(msg.timestamp),
      })),
    }));
  } catch {
    return [];
  }
}

export function getChat(id: string): Chat | null {
  const chats = getChats();
  return chats.find(c => c.id === id) || null;
}

export function deleteChat(id: string): void {
  const chats = getChats().filter(c => c.id !== id);
  localStorage.setItem(STORAGE_KEY, JSON.stringify(chats));
}

export function updateChat(id: string, updates: Partial<Chat>): void {
  const chat = getChat(id);
  if (!chat) return;
  
  const updated = { ...chat, ...updates, updatedAt: new Date() };
  saveChat(updated);
}
