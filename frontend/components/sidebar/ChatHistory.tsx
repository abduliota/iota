'use client';

import React, { useEffect, useState } from 'react';
import { Chat } from '@/lib/types';
import { getChats, deleteChat } from '@/lib/storage';
import { ChatItem } from './ChatItem';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';

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
    <div className="flex flex-col h-full transition-colors duration-200">
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
    </div>
  );
}
