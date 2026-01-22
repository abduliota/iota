'use client';

import React, { useState, useEffect } from 'react';
import { v4 as uuidv4 } from 'uuid';
import { Chat, Message } from '@/lib/types';
import { getChat, saveChat } from '@/lib/storage';
import { ChatInterface } from '@/components/chat/ChatInterface';
import { ChatHistory } from '@/components/sidebar/ChatHistory';
import { SourcePanel } from '@/components/chat/SourcePanel';

export default function Home() {
  const [selectedChatId, setSelectedChatId] = useState<string | null>(null);
  const [currentChat, setCurrentChat] = useState<Chat | null>(null);
  const [showSources, setShowSources] = useState(false);
  const [theme, setTheme] = useState<'light' | 'dark'>('light');

  useEffect(() => {
    const savedTheme = localStorage.getItem('theme') as 'light' | 'dark' | null;
    const initialTheme = savedTheme || 'light';
    setTheme(initialTheme);
    if (initialTheme === 'dark') {
      document.documentElement.classList.add('dark');
    }
  }, []);

  const toggleTheme = () => {
    const newTheme = theme === 'light' ? 'dark' : 'light';
    setTheme(newTheme);
    localStorage.setItem('theme', newTheme);
    if (newTheme === 'dark') {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  };

  useEffect(() => {
    if (selectedChatId) {
      const chat = getChat(selectedChatId);
      setCurrentChat(chat);
    } else {
      setCurrentChat(null);
    }
  }, [selectedChatId]);

  const handleNewMessage = (message: Message) => {
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
    <div className="flex h-screen bg-white dark:bg-gray-900 transition-colors duration-200">
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
            />
          ) : (
            <ChatInterface 
              messages={[]}
              onNewMessage={handleNewMessage}
            />
          )}
        </div>
        <button
          onClick={toggleTheme}
          className="absolute top-4 right-4 p-2 rounded-lg bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-600 shadow-md hover:shadow-lg hover:shadow-blue-200/30 dark:hover:shadow-blue-500/20 transition-all duration-200 transform hover:scale-110 z-20"
          aria-label="Toggle theme"
        >
          {theme === 'light' ? '🌙' : '☀️'}
        </button>
        {allReferences.length > 0 && (
          <button
            onClick={() => setShowSources(!showSources)}
            className="absolute top-4 right-20 px-4 py-2 bg-blue-600 dark:bg-blue-500 text-white rounded-lg hover:bg-blue-700 dark:hover:bg-blue-600 shadow-md hover:shadow-lg hover:shadow-blue-300/50 dark:hover:shadow-blue-500/30 z-10 transition-all duration-200 transform hover:scale-105 active:scale-95"
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
    </div>
  );
}
