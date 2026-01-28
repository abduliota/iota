'use client';

import React, { useState, useEffect, useRef } from 'react';
import { Message } from '@/lib/types';
import { AnimatedMessage } from './AnimatedMessage';
import { AnimatedInput } from './AnimatedInput';
import { AnimatedTypingIndicator } from './AnimatedTypingIndicator';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';

interface ChatInterfaceProps {
  messages: Message[];
  onNewMessage: (message: Message) => void;
  canSend?: boolean;
  onLimitReached?: () => void;
}

export function ChatInterface({ messages, onNewMessage, canSend = true, onLimitReached }: ChatInterfaceProps) {
  const [localMessages, setLocalMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [streamingContent, setStreamingContent] = useState('');
  const [activeTab, setActiveTab] = useState('answer');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const skipSyncRef = useRef(false);

  useEffect(() => {
    if (skipSyncRef.current) {
      skipSyncRef.current = false;
      return;
    }
    setLocalMessages(messages);
  }, [messages]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [localMessages, streamingContent]);

  const handleSend = async (content: string) => {
    if (!canSend) {
      onLimitReached?.();
      return;
    }

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content,
      timestamp: new Date(),
    };
    setLocalMessages(prev => [...prev, userMessage]);
    skipSyncRef.current = true;
    onNewMessage(userMessage);

    setIsLoading(true);
    setStreamingContent('');

    let fullContent = '';
    let references: any[] = [];

    try {
      const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const response = await fetch(`${API_URL}/api/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ message: content }),
      });

      if (!response.ok) {
        throw new Error('API request failed');
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (!reader) {
        throw new Error('No response body');
      }

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = JSON.parse(line.slice(6));
            
            if (data.type === 'token') {
              fullContent += data.content;
              setStreamingContent(fullContent);
            } else if (data.type === 'done') {
              references = data.references || [];
            }
          }
        }
      }

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: fullContent,
        references: references,
        timestamp: new Date(),
      };
      setLocalMessages(prev => [...prev, assistantMessage]);
      skipSyncRef.current = true;
      onNewMessage(assistantMessage);
      setIsLoading(false);
      setStreamingContent('');
    } catch (error) {
      console.error('Chat error:', error);
      setIsLoading(false);
      setStreamingContent('');
    }
  };

  const allMessages = [...localMessages];
  if (streamingContent) {
    allMessages.push({
      id: 'streaming',
      role: 'assistant',
      content: streamingContent,
      timestamp: new Date(),
    });
  }

  return (
    <div className="flex h-full">
      <div className="flex flex-col flex-1 bg-background text-foreground transition-colors duration-200 rounded-none sm:rounded-2xl border border-border/60 overflow-hidden">
        {/* Chat header */}
        <div className="flex items-center justify-between px-3 sm:px-4 py-2.5 border-b border-border/70 bg-background/90 backdrop-blur-sm">
          <div className="flex flex-col gap-0.5">
            <span className="text-xs uppercase tracking-wide text-muted-foreground/80">
              Conversation
            </span>
            <span className="text-sm font-medium text-foreground">
              KSA Regulatory Assistant
            </span>
          </div>
          <div className="flex items-center gap-2">
            <Tabs value={activeTab} onValueChange={setActiveTab}>
              <TabsList className="bg-muted/60 h-8 px-1 rounded-full">
                <TabsTrigger
                  value="answer"
                  className="data-[state=active]:bg-background data-[state=active]:text-foreground rounded-full px-3 py-1 text-xs"
                >
                  Answer
                </TabsTrigger>
                <TabsTrigger
                  value="links"
                  className="data-[state=active]:bg-background data-[state=active]:text-foreground rounded-full px-3 py-1 text-xs"
                >
                  Links
                </TabsTrigger>
              </TabsList>
            </Tabs>
          </div>
        </div>

        {/* Messages area */}
        <div className="flex-1 min-h-0">
          <ScrollArea className="h-full px-3 sm:px-4 lg:px-6 py-4">
            {allMessages.length === 0 ? (
              <div className="flex items-center justify-center h-full">
                <div className="max-w-md w-full rounded-2xl border border-border/60 bg-muted/40 px-5 py-6 text-left shadow-sm">
                  <h2 className="text-base sm:text-lg font-semibold text-foreground mb-2">
                    Ask KSA regulatory questions
                  </h2>
                  <p className="text-xs sm:text-sm text-muted-foreground mb-4">
                    Get clear, grounded answers on Saudi regulatory frameworks, requirements, and compliance workflows.
                  </p>
                  <div className="flex flex-col sm:flex-row sm:items-center gap-2">
                    <button
                      onClick={() =>
                        handleSend('What are the key KSA regulatory requirements for fintech startups?')
                      }
                      className="w-full sm:w-auto px-3 py-2 rounded-2xl text-xs sm:text-sm border border-border bg-background hover:bg-muted/80 transition-colors"
                    >
                      KSA fintech regulatory overview
                    </button>
                    <button
                      onClick={() =>
                        handleSend('Summarize the main AML and CTF requirements in KSA.')
                      }
                      className="w-full sm:w-auto px-3 py-2 rounded-2xl text-xs sm:text-sm border border-border/70 bg-muted/40 hover:bg-muted/70 transition-colors"
                    >
                      AML / CTF summary
                    </button>
                  </div>
                </div>
              </div>
            ) : (
              <div className="flex flex-col gap-3">
                {allMessages.map((msg, index) => (
                  <AnimatedMessage key={msg.id} message={msg} index={index} />
                ))}
                {isLoading && !streamingContent && <AnimatedTypingIndicator />}
                <div ref={messagesEndRef} />
              </div>
            )}
          </ScrollArea>
        </div>

        {/* Input bar */}
        <div className="border-t border-border/70 bg-background/95 backdrop-blur-sm px-2 sm:px-4 lg:px-6 py-3">
          <AnimatedInput
            onSend={handleSend}
            disabled={isLoading}
            canSend={canSend}
            onLimitReached={onLimitReached}
          />
        </div>
      </div>
    </div>
  );
}
