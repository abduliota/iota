'use client';

import React from 'react';
import ReactMarkdown from 'react-markdown';
import { Message } from '@/lib/types';
import { References } from './References';
import { Button } from '@/components/ui/button';
import { Download, Copy } from 'lucide-react';

interface MessageBubbleProps {
  message: Message;
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === 'user';

  const copyToClipboard = () => {
    navigator.clipboard.writeText(message.content);
  };

  const downloadMessage = () => {
    const blob = new Blob([message.content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `message-${message.id}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}>
      <div className={`max-w-[80%] rounded-lg p-4 transition-all duration-200 ${isUser ? 'bg-blue-500 text-white' : 'bg-[#1a1a1a] text-gray-100'}`}>
        {isUser ? (
          <div className="whitespace-pre-wrap">{message.content}</div>
        ) : (
          <>
            <div className="prose prose-sm max-w-none prose-invert">
              <ReactMarkdown>{message.content}</ReactMarkdown>
            </div>
            {message.references && <References references={message.references} />}
            <div className="mt-2 flex gap-2">
              <Button
                variant="ghost"
                size="sm"
                onClick={downloadMessage}
                className="text-xs h-8"
              >
                <Download className="h-3 w-3 mr-1" />
                Download
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={copyToClipboard}
                className="text-xs h-8"
              >
                <Copy className="h-3 w-3 mr-1" />
                Copy
              </Button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
