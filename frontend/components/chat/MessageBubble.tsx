'use client';

import React, { useState } from 'react';
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
  const [showSources, setShowSources] = useState(false);

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
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-3`}>
      <div
        className={`max-w-[80%] text-sm leading-relaxed transition-all duration-200 ${
          isUser
            ? 'bg-primary text-primary-foreground rounded-2xl rounded-br-sm px-3 py-2.5'
            : 'bg-muted/70 text-foreground rounded-2xl rounded-bl-sm px-3 py-2.5'
        }`}
      >
        {isUser ? (
          <div className="whitespace-pre-wrap break-words">
            {message.content}
          </div>
        ) : (
          <>
            <div className="prose prose-sm max-w-none prose-invert prose-pre:bg-transparent prose-pre:p-0 prose-code:text-xs">
              <ReactMarkdown>{message.content}</ReactMarkdown>
            </div>
            {message.references && message.references.length > 0 && (
              <div className="mt-2 flex items-center gap-2">
                <button
                  type="button"
                  className={`text-xs px-2 py-1 rounded-full border transition-colors ${
                    !showSources
                      ? 'bg-muted text-foreground border-border'
                      : 'bg-background text-foreground border-border'
                  }`}
                  onClick={() => setShowSources(false)}
                >
                  Answer
                </button>
                <button
                  type="button"
                  className={`text-xs px-2 py-1 rounded-full border transition-colors ${
                    showSources
                      ? 'bg-muted text-foreground border-border'
                      : 'bg-background text-foreground border-border'
                  }`}
                  onClick={() => setShowSources(true)}
                >
                  Sources ({message.references.length})
                </button>
              </div>
            )}
            {showSources && message.references && message.references.length > 0 && (
              <div className="mt-3">
                <References references={message.references} />
              </div>
            )}
            <div className="mt-2 flex flex-wrap gap-1.5">
              <Button
                variant="ghost"
                size="sm"
                onClick={downloadMessage}
                className="text-[11px] h-7 px-2"
              >
                <Download className="h-3 w-3 mr-1" />
                Download
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={copyToClipboard}
                className="text-[11px] h-7 px-2"
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
