'use client';

import React from 'react';
import ReactMarkdown from 'react-markdown';
import { Message } from '@/lib/types';
import { References } from './References';
import { Button } from '@/components/ui/button';

interface MessageBubbleProps {
  message: Message;
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === 'user';

  const copyToClipboard = () => {
    navigator.clipboard.writeText(message.content);
  };

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}>
      <div className={`max-w-[80%] rounded-lg p-4 transition-all duration-200 ${isUser ? 'bg-blue-600 dark:bg-blue-500 text-white' : 'bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-gray-100'}`}>
        {isUser ? (
          <div className="whitespace-pre-wrap">{message.content}</div>
        ) : (
          <>
            <div className="prose prose-sm max-w-none dark:prose-invert">
              <ReactMarkdown>{message.content}</ReactMarkdown>
            </div>
            {message.references && <References references={message.references} />}
            <div className="mt-2">
              <Button
                variant="ghost"
                onClick={copyToClipboard}
                className="text-xs p-1 h-auto"
              >
                Copy
              </Button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
