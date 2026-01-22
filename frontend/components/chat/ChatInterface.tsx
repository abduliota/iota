'use client';

import React, { useState, useEffect, useRef } from 'react';
import { Message } from '@/lib/types';
import { MessageBubble } from './MessageBubble';
import { ChatInput } from './ChatInput';
import { TypingIndicator } from './TypingIndicator';
import { ScrollArea } from '@/components/ui/scroll-area';
import { mockStreamResponse } from '@/lib/mock-streaming';

interface ChatInterfaceProps {
  messages: Message[];
  onNewMessage: (message: Message) => void;
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

export function ChatInterface({ messages, onNewMessage }: ChatInterfaceProps) {
  const [isLoading, setIsLoading] = useState(false);
  const [streamingContent, setStreamingContent] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingContent]);

  const handleSend = (content: string) => {
    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content,
      timestamp: new Date(),
    };
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
        onNewMessage(assistantMessage);
        setIsLoading(false);
        setStreamingContent('');
      }
    );
  };

  const allMessages = [...messages];
  if (streamingContent) {
    allMessages.push({
      id: 'streaming',
      role: 'assistant',
      content: streamingContent,
      timestamp: new Date(),
    });
  }

  return (
    <div className="flex flex-col h-screen bg-white dark:bg-gray-900 transition-colors duration-200">
      <ScrollArea className="flex-1 p-4 bg-white dark:bg-gray-900">
        {allMessages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <h2 className="text-2xl font-semibold mb-4 text-gray-900 dark:text-white">Ask questions about your PDFs</h2>
            <div className="space-y-2">
              <button
                onClick={() => handleSend('What is LoRA?')}
                className="px-4 py-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-white border border-gray-300 dark:border-gray-600 rounded-lg text-sm shadow-md hover:shadow-lg hover:shadow-blue-200/50 dark:hover:shadow-blue-500/30 hover:border-blue-400 dark:hover:border-blue-500 transition-all duration-200 transform hover:scale-105 active:scale-95"
              >
                What is LoRA?
              </button>
              <button
                onClick={() => handleSend('Summarize this document')}
                className="px-4 py-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-white border border-gray-300 dark:border-gray-600 rounded-lg text-sm shadow-md hover:shadow-lg hover:shadow-blue-200/50 dark:hover:shadow-blue-500/30 hover:border-blue-400 dark:hover:border-blue-500 transition-all duration-200 transform hover:scale-105 active:scale-95"
              >
                Summarize this document
              </button>
            </div>
          </div>
        ) : (
          <>
            {allMessages.map((msg) => (
              <MessageBubble key={msg.id} message={msg} />
            ))}
            {isLoading && !streamingContent && <TypingIndicator />}
            <div ref={messagesEndRef} />
          </>
        )}
      </ScrollArea>
      <ChatInput onSend={handleSend} disabled={isLoading} />
    </div>
  );
}
