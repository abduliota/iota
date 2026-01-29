'use client';

import React, { useState, useEffect } from 'react';
import { v4 as uuidv4 } from 'uuid';
import { Chat, Message } from '@/lib/types';
import { getChat, saveChat } from '@/lib/storage';
import { ChatInterface } from '@/components/chat/ChatInterface';
import { ChatHistory } from '@/components/sidebar/ChatHistory';
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
      <aside className="hidden md:flex md:flex-col md:w-64 lg:w-72 border-r border-border bg-card/40">
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
          <span className="text-sm font-medium text-muted-foreground">
            KSA Regulatory Assistant
          </span>
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

        {/* Centered chat content */}
        <div className="flex-1 min-h-0 flex flex-col items-center overflow-hidden">
          <div className="hidden md:flex w-full max-w-3xl lg:max-w-4xl xl:max-w-5xl px-2 sm:px-4 lg:px-6 justify-end py-2">
            <Button
              size="sm"
              variant="outline"
              className="rounded-full text-xs"
              onClick={() => setSelectedChatId(null)}
            >
              + New chat
            </Button>
          </div>
          <div className="flex-1 min-h-0 w-full max-w-3xl lg:max-w-4xl xl-max-w-5xl px-2 sm:px-4 lg:px-6 flex relative">
            <div className="flex-1">
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
