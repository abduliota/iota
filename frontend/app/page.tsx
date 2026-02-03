'use client';

import React, { useState, useEffect } from 'react';
import { v4 as uuidv4 } from 'uuid';
import { Chat, Message } from '@/lib/types';
import { getChat, saveChat } from '@/lib/storage';
import { ChatInterface } from '@/components/chat/ChatInterface';
import { ChatHistory } from '@/components/sidebar/ChatHistory';
import { SummaryCard } from '@/components/dashboard/SummaryCard';
import { LatestSourcesPanel } from '@/components/dashboard/LatestSourcesPanel';
import { usePromptLimit } from '@/hooks/usePromptLimit';
import { useFingerprintAuth } from '@/hooks/useFingerprintAuth';
import { PromptCounter } from '@/components/auth/PromptCounter';
import { AuthModal } from '@/components/auth/AuthModal';
import { Button } from '@/components/ui/button';
import { Menu } from 'lucide-react';

export default function Home() {
  const [selectedChatId, setSelectedChatId] = useState<string | null>(null);
  const [currentChat, setCurrentChat] = useState<Chat | null>(null);
  const [showAuthModal, setShowAuthModal] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const { remainingPrompts, canSend, incrementPrompt, resetPrompts } = usePromptLimit();
  const { isAuthenticated, register, login, logout } = useFingerprintAuth();

  useEffect(() => {
    document.documentElement.classList.add('dark');
  }, []);

  useEffect(() => {
    if (isAuthenticated) {
      resetPrompts();
    }
  }, [isAuthenticated]);

  useEffect(() => {
    if (selectedChatId) {
      const chat = getChat(selectedChatId);
      setCurrentChat(chat);
    } else {
      setCurrentChat(null);
    }
  }, [selectedChatId]);

  const handleNewMessage = (message: Message) => {
    if (message.role === 'user' && !isAuthenticated) {
      incrementPrompt();
    }

    let chat: Chat;

    if (!currentChat) {
      const title = message.role === 'user' 
        ? message.content.slice(0, 50) 
        : 'New Chat';
      
      chat = {
        id: uuidv4(),
        title,
        messages: [message],
        createdAt: new Date(),
        updatedAt: new Date(),
      };
      setCurrentChat(chat);
      setSelectedChatId(chat.id);
    } else {
      chat = {
        ...currentChat,
        messages: [...currentChat.messages, message],
        updatedAt: new Date(),
      };
      setCurrentChat(chat);
    }

    saveChat(chat);
  };

  const latestRefs = currentChat?.messages
    ? [...currentChat.messages].reverse().find((m) => m.role === 'assistant' && m.references?.length)?.references ?? null
    : null;

  return (
    <div className="flex h-screen bg-background text-foreground transition-colors duration-200">
      {/* Prompt counter pinned to top center */}
      <div className="hidden md:flex absolute top-4 left-1/2 -translate-x-1/2 z-30">
        <PromptCounter
          remaining={remainingPrompts}
          total={10}
          isAuthenticated={isAuthenticated}
        />
      </div>

      {/* Desktop / tablet sidebar */}
      <aside className="hidden md:flex md:flex-col md:w-64 lg:w-72 shrink-0 border-r border-border bg-card">
        {/* Logo header */}
        <div className="flex items-center gap-2 px-4 py-3 border-b border-border">
          <img src="/logo.jpeg" alt="IOTA Technologies" className="h-8 w-8" />
          <span className="text-sm font-medium text-foreground">
            IOTA Technologies
          </span>
        </div>
        <ChatHistory 
          selectedChatId={selectedChatId} 
          onSelectChat={setSelectedChatId}
        />
      </aside>

      {/* Main area */}
      <main className="flex-1 flex flex-col">
        {/* Mobile header with menu button */}
        <header className="flex items-center justify-between px-3 py-2 border-b border-border md:hidden bg-background/80 backdrop-blur-sm">
          <Button
            size="icon"
            variant="ghost"
            className="rounded-full"
            aria-label="Open chat history"
            onClick={() => setIsSidebarOpen(true)}
          >
            <Menu className="h-5 w-5" />
          </Button>
          <div className="flex items-center gap-2">
            <img src="/logo.jpeg" alt="IOTA Technologies" className="h-6 w-6" />
            <span className="text-sm font-medium text-muted-foreground">
              IOTA Technologies
            </span>
          </div>
          <div className="flex items-center gap-2">
            <PromptCounter
              remaining={remainingPrompts}
              total={10}
              isAuthenticated={isAuthenticated}
            />
            <Button
              size="icon"
              variant="outline"
              className="h-7 w-7 rounded-full"
              aria-label="Start new chat"
              onClick={() => setSelectedChatId(null)}
            >
              +
            </Button>
          </div>
        </header>

        {/* Mobile slide-in sidebar */}
        {isSidebarOpen && (
          <div className="fixed inset-0 z-40 flex md:hidden">
            <div
              className="absolute inset-0 bg-black/40"
              onClick={() => setIsSidebarOpen(false)}
            />
            <div className="relative z-50 h-full w-72 max-w-full bg-background border-r border-border shadow-lg flex flex-col">
              <div className="flex items-center justify-between px-3 py-2 border-b border-border">
                <span className="text-sm font-medium">
                  Chats
                </span>
                <button
                  className="text-xs text-muted-foreground hover:text-foreground"
                  onClick={() => setIsSidebarOpen(false)}
                  aria-label="Close sidebar"
                >
                  ✕
                </button>
              </div>
              <ChatHistory 
                selectedChatId={selectedChatId} 
                onSelectChat={(id) => {
                  setSelectedChatId(id);
                  setIsSidebarOpen(false);
                }}
              />
            </div>
          </div>
        )}

        {/* Regulation AI dashboard: summary card + two-column chat/sources */}
        <div className="flex-1 min-h-0 flex flex-col overflow-auto">
          <div className="mx-auto w-full max-w-[1200px] px-4 py-4 md:px-6 md:py-6">
            <SummaryCard />
            <div className="mt-6 flex flex-1 min-h-0 gap-4 md:gap-6">
              <div className="flex-1 min-w-0 flex flex-col rounded-xl border border-border bg-card shadow-sm">
                {currentChat ? (
                  <ChatInterface
                    messages={currentChat.messages}
                    onNewMessage={handleNewMessage}
                    canSend={isAuthenticated || canSend}
                    onLimitReached={() => setShowAuthModal(true)}
                  />
                ) : (
                  <ChatInterface
                    messages={[]}
                    onNewMessage={handleNewMessage}
                    canSend={isAuthenticated || canSend}
                    onLimitReached={() => setShowAuthModal(true)}
                  />
                )}
              </div>
              <div className="hidden lg:block w-80 shrink-0">
                <LatestSourcesPanel references={latestRefs} />
              </div>
            </div>
          </div>
        </div>

        <AuthModal
          isOpen={showAuthModal}
          onClose={() => setShowAuthModal(false)}
          onSuccess={() => {}}
          onRegister={register}
          onLogin={login}
        />
      </main>
    </div>
  );
}
