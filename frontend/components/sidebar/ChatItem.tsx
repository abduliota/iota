import React from 'react';
import { Chat } from '@/lib/types';
import { Button } from '@/components/ui/button';

interface ChatItemProps {
  chat: Chat;
  isSelected: boolean;
  onClick: () => void;
  onDelete: () => void;
}

export function ChatItem({ chat, isSelected, onClick, onDelete }: ChatItemProps) {
  const formatDate = (date: Date) => {
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));
    
    if (days === 0) return 'Today';
    if (days === 1) return 'Yesterday';
    if (days < 7) return `${days} days ago`;
    return date.toLocaleDateString();
  };

  return (
    <div
      onClick={onClick}
      className={`group p-3 rounded-lg cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-800 transition-all duration-200 ${
        isSelected ? 'bg-blue-50 dark:bg-blue-900 border border-blue-200 dark:border-blue-700' : ''
      }`}
    >
      <div className="flex justify-between items-start">
        <div className="flex-1 min-w-0">
          <div className="font-medium text-sm truncate dark:text-white">{chat.title}</div>
          <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">{formatDate(chat.updatedAt)}</div>
        </div>
        <Button
          variant="ghost"
          onClick={(e) => {
            e.stopPropagation();
            onDelete();
          }}
          className="text-xs p-1 h-auto opacity-0 group-hover:opacity-100"
        >
          ✕
        </Button>
      </div>
    </div>
  );
}
