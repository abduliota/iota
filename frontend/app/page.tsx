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
import { ThemeToggle } from '@/components/ui/ThemeToggle';
import { Menu } from 'lucide-react';

export default function Home() {
  const [selectedChatId, setSelectedChatId] = useState<string | null>(null);
  const [currentChat, setCurrentChat] = useState<Chat | null>(null);
  const [showAuthModal, setShowAuthModal] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const { remainingPrompts, canSend, incrementPrompt, resetPrompts } = usePromptLimit();
  const { isAuthenticated, register, login, logout } = useFingerprintAuth();

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
      {/* Desktop sidebar - ChatGPT style, 260px */}
      <aside className="hidden md:flex md:flex-col w-[260px] shrink-0 border-r border-border bg-sidebar-bg transition-[background-color] duration-200">
        <div className="flex items-center justify-between gap-2.5 px-3 py-3 border-b border-border">
          <div className="flex min-w-0 flex-1 items-center gap-2.5">
            <img
              src="/logo.jpeg"
              alt="IOTA Technologies"
              className="h-[38px] w-[52px] shrink-0 rounded-lg"
              draggable={false}
            />
            <span className="truncate text-[15px] font-medium text-foreground">
              IOTA Technologies
            </span>
          </div>
          <ThemeToggle />
        </div>
        <ChatHistory
          selectedChatId={selectedChatId}
          onSelectChat={setSelectedChatId}
        />
      </aside>

      {/* Main area */}
      <main className="flex-1 flex flex-col">
        {/* Mobile header: left menu+logo+name, right badge+toggle+new chat */}
        <header className="flex items-center justify-between gap-2 px-3 py-2 border-b border-border md:hidden bg-background/95 backdrop-blur-sm transition-colors duration-200">
          <div className="flex min-w-0 flex-1 items-center gap-2">
            <Button
              size="icon"
              variant="ghost"
              className="h-9 w-9 shrink-0 rounded-full"
              aria-label="Open chat history"
              onClick={() => setIsSidebarOpen(true)}
            >
              <Menu className="h-5 w-5" />
            </Button>
            <img
              src="/logo.jpeg"
              alt="IOTA Technologies"
              className="h-[38px] w-[52px] shrink-0 rounded-lg"
              draggable={false}
            />
            <span className="truncate text-[15px] font-medium text-foreground">
              IOTA Technologies
            </span>
          </div>
          <div className="flex shrink-0 items-center gap-2">
            <PromptCounter
              remaining={remainingPrompts}
              total={10}
              isAuthenticated={isAuthenticated}
            />
            <ThemeToggle />
            <Button
              size="icon"
              variant="outline"
              className="h-8 w-8 rounded-full"
              aria-label="Start new chat"
              onClick={() => setSelectedChatId(null)}
            >
              +
            </Button>
          </div>
        </header>

        {/* Mobile off-canvas drawer - same sidebar style */}
        {isSidebarOpen && (
          <div className="fixed inset-0 z-40 flex md:hidden">
            <div
              className="absolute inset-0 bg-black/40 transition-opacity duration-200"
              onClick={() => setIsSidebarOpen(false)}
              aria-hidden
            />
            <div className="relative z-50 h-full w-[260px] max-w-[85vw] bg-sidebar-bg border-r border-border shadow-xl flex flex-col transition-transform duration-200">
              <div className="flex items-center justify-between px-3 py-3 border-b border-border shrink-0">
                <span className="text-sm font-medium text-foreground">Chats</span>
                <button
                  type="button"
                  className="rounded-md p-1.5 text-muted-foreground hover:text-foreground hover:bg-sidebar-hover transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-accent"
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
        <div className="flex-1 min-h-0 flex flex-col overflow-hidden">
          <div className="mx-auto w-full max-w-[1200px] flex flex-1 min-h-0 flex-col px-4 py-4 md:px-6 md:py-6">
            <SummaryCard
              rightSlot={
                <PromptCounter
                  remaining={remainingPrompts}
                  total={10}
                  isAuthenticated={isAuthenticated}
                />
              }
            />
            <div className="mt-6 flex flex-1 min-h-0 gap-4 md:gap-6">
              <div className="flex-1 min-h-0 min-w-0 flex flex-col rounded-xl border border-border bg-card shadow-sm">
                {currentChat ? (
                  <ChatInterface
                    key={currentChat.id}
                    messages={currentChat.messages}
                    onNewMessage={handleNewMessage}
                    canSend={isAuthenticated || canSend}
                    onLimitReached={() => setShowAuthModal(true)}
                  />
                ) : (
                  <ChatInterface
                    key="new"
                    messages={[]}
                    onNewMessage={handleNewMessage}
                    canSend={isAuthenticated || canSend}
                    onLimitReached={() => setShowAuthModal(true)}
                  />
                )}
              </div>
              <div className="hidden lg:flex lg:flex-col w-80 shrink-0 min-h-0">
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
