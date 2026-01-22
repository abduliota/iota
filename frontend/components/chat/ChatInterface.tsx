'use client';

import React, { useState, useEffect, useRef } from 'react';
import { Message } from '@/lib/types';
import { AnimatedMessage } from './AnimatedMessage';
import { AnimatedInput } from './AnimatedInput';
import { AnimatedTypingIndicator } from './AnimatedTypingIndicator';
import { ScrollArea } from '@/components/ui/scroll-area';
import { mockStreamResponse } from '@/lib/mock-streaming';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';

interface ChatInterfaceProps {
  messages: Message[];
  onNewMessage: (message: Message) => void;
  canSend?: boolean;
  onLimitReached?: () => void;
}

const MOCK_RESPONSES = [
  {
    content: 'LoRA (Low-Rank Adaptation) is a parameter-efficient fine-tuning method that reduces the number of trainable parameters by using low-rank matrices.',
    references: [
      { id: '1', source: 'research_paper.pdf', page: 3, snippet: 'LoRA introduces trainable rank decomposition matrices...' },
      { id: '2', source: 'huggingface_blog.pdf', page: 1, snippet: 'Parameter-efficient fine-tuning with LoRA...' },
    ],
  },
  {
    content: 'Based on the documents, here is a summary of the key points...',
    references: [
      { id: '1', source: 'document.pdf', page: 5, snippet: 'Key findings suggest...' },
    ],
  },
];

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

  const handleSend = (content: string) => {
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

    const mockResponse = MOCK_RESPONSES[Math.floor(Math.random() * MOCK_RESPONSES.length)];
    let fullContent = '';

    mockStreamResponse(
      mockResponse.content,
      (chunk) => {
        fullContent += chunk;
        setStreamingContent(fullContent);
      },
      () => {
        const assistantMessage: Message = {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: fullContent,
          references: mockResponse.references,
          timestamp: new Date(),
        };
        setLocalMessages(prev => [...prev, assistantMessage]);
        skipSyncRef.current = true;
        onNewMessage(assistantMessage);
        setIsLoading(false);
        setStreamingContent('');
      }
    );
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
