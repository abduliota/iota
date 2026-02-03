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
  return (
    <div
      role="button"
      tabIndex={0}
      onClick={onClick}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onClick();
        }
      }}
      className={`group flex items-center gap-2 rounded-md px-3 py-2.5 text-left text-sm font-normal leading-snug transition-colors duration-150 cursor-pointer outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-sidebar-bg ${
        isSelected
          ? 'bg-sidebar-active text-foreground border-l-2 border-l-accent -ml-[2px] pl-[10px]'
          : 'text-muted-foreground hover:bg-sidebar-hover hover:text-foreground'
      }`}
    >
      <span className="flex-1 min-w-0 truncate" title={chat.title}>
        {chat.title}
      </span>
      <Button
        variant="ghost"
        size="icon"
        onClick={(e) => {
          e.stopPropagation();
          e.preventDefault();
          onDelete();
        }}
        className="h-7 w-7 shrink-0 rounded opacity-0 group-hover:opacity-100 transition-opacity duration-150 text-muted-foreground hover:text-foreground focus-visible:opacity-100"
        aria-label="Delete chat"
      >
        <span className="text-xs">✕</span>
      </Button>
    </div>
  );
}
