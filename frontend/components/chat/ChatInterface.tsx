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
      const response = await fetch('http://localhost:8000/api/chat', {
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
    <div className="flex flex-col h-screen bg-[#0a0a0a] transition-colors duration-200">
      <div className="border-b border-gray-800 px-4 py-2">
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="bg-transparent">
            <TabsTrigger value="answer" className="data-[state=active]:bg-gray-800">Answer</TabsTrigger>
            <TabsTrigger value="links" className="data-[state=active]:bg-gray-800">Links</TabsTrigger>
          </TabsList>
        </Tabs>
      </div>
      <ScrollArea className="flex-1 p-4 bg-[#0a0a0a]">
        {allMessages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <h2 className="text-2xl font-semibold mb-4 text-white">Ask KSA regulatory questions</h2>
            <div className="space-y-2">
              <button
                onClick={() => handleSend('What is LoRA?')}
                className="px-4 py-2 bg-gray-700 text-white border border-gray-600 rounded-lg text-sm shadow-md hover:shadow-lg hover:shadow-blue-500/30 hover:border-blue-500 transition-all duration-200 transform hover:scale-105 active:scale-95"
              >
                What is LoRA?
              </button>
              <button
                onClick={() => handleSend('Summarize this document')}
                className="px-4 py-2 bg-gray-700 text-white border border-gray-600 rounded-lg text-sm shadow-md hover:shadow-lg hover:shadow-blue-500/30 hover:border-blue-500 transition-all duration-200 transform hover:scale-105 active:scale-95"
              >
                Summarize this document
              </button>
            </div>
          </div>
        ) : (
          <>
            {allMessages.map((msg, index) => (
              <AnimatedMessage key={msg.id} message={msg} index={index} />
            ))}
            {isLoading && !streamingContent && <AnimatedTypingIndicator />}
            <div ref={messagesEndRef} />
          </>
        )}
      </ScrollArea>
      <AnimatedInput onSend={handleSend} disabled={isLoading} canSend={canSend} onLimitReached={onLimitReached} />
    </div>
  );
}
