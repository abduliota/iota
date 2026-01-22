'use client';

import React, { useEffect, useState } from 'react';
import { Chat } from '@/lib/types';
import { getChats, deleteChat } from '@/lib/storage';
import { ChatItem } from './ChatItem';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { IngestCard } from '@/components/ingest/IngestCard';

interface ChatHistoryProps {
  selectedChatId: string | null;
  onSelectChat: (chatId: string | null) => void;
}

export function ChatHistory({ selectedChatId, onSelectChat }: ChatHistoryProps) {
  const [chats, setChats] = useState<Chat[]>([]);

  useEffect(() => {
    setChats(getChats());
  }, []);

  const handleNewChat = () => {
    onSelectChat(null);
  };

  const handleDelete = (chatId: string) => {
    deleteChat(chatId);
    setChats(getChats());
    if (selectedChatId === chatId) {
      onSelectChat(null);
    }
  };

  return (
    <div className="w-64 border-r border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900 flex flex-col transition-colors duration-200">
      <div className="p-4 border-b border-gray-200 dark:border-gray-700">
        <Button onClick={handleNewChat} className="w-full">
          + New Chat
        </Button>
      </div>
      <ScrollArea className="flex-1 p-2">
        <div className="space-y-2">
          {chats.map((chat) => (
            <ChatItem
              key={chat.id}
              chat={chat}
              isSelected={selectedChatId === chat.id}
              onClick={() => onSelectChat(chat.id)}
              onDelete={() => handleDelete(chat.id)}
            />
          ))}
        </div>
      </ScrollArea>
      <div className="p-2">
        <IngestCard />
      </div>
    </div>
  );
}
