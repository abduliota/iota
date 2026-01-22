'use client';

import React, { useState, useEffect } from 'react';
import { v4 as uuidv4 } from 'uuid';
import { Chat, Message } from '@/lib/types';
import { getChat, saveChat } from '@/lib/storage';
import { ChatInterface } from '@/components/chat/ChatInterface';
import { ChatHistory } from '@/components/sidebar/ChatHistory';
import { SourcePanel } from '@/components/chat/SourcePanel';
import { usePromptLimit } from '@/hooks/usePromptLimit';
import { useFingerprintAuth } from '@/hooks/useFingerprintAuth';
import { PromptCounter } from '@/components/auth/PromptCounter';
import { AuthModal } from '@/components/auth/AuthModal';

export default function Home() {
  const [selectedChatId, setSelectedChatId] = useState<string | null>(null);
  const [currentChat, setCurrentChat] = useState<Chat | null>(null);
  const [showSources, setShowSources] = useState(false);
  const [showAuthModal, setShowAuthModal] = useState(false);
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

  const allReferences = currentChat?.messages
    .flatMap(msg => msg.references || [])
    .filter((ref, index, self) => 
      index === self.findIndex(r => r.id === ref.id)
    ) || [];

  return (
    <div className="flex h-screen bg-[#0a0a0a] transition-colors duration-200">
      <div className="absolute top-4 left-1/2 transform -translate-x-1/2 z-30">
        <PromptCounter
          remaining={remainingPrompts}
          total={10}
          isAuthenticated={isAuthenticated}
        />
      </div>
      <ChatHistory 
        selectedChatId={selectedChatId} 
        onSelectChat={setSelectedChatId}
      />
      <div className="flex-1 flex relative">
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
        {allReferences.length > 0 && (
          <button
            onClick={() => setShowSources(!showSources)}
            className="absolute top-4 right-4 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 shadow-md hover:shadow-lg hover:shadow-blue-500/30 z-10 transition-all duration-200 transform hover:scale-105 active:scale-95"
          >
            {showSources ? 'Hide' : 'Show'} Sources
          </button>
        )}
        <SourcePanel 
          sources={allReferences}
          isOpen={showSources}
          onClose={() => setShowSources(false)}
        />
      </div>
      <AuthModal
        isOpen={showAuthModal}
        onClose={() => setShowAuthModal(false)}
        onSuccess={() => {}}
        onRegister={register}
        onLogin={login}
      />
    </div>
  );
}
