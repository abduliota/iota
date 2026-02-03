'use client';

import React, { useState, KeyboardEvent, useRef, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Send, Paperclip, Mic } from 'lucide-react';
import { motion } from 'framer-motion';

interface AnimatedInputProps {
  onSend: (message: string) => void;
  disabled?: boolean;
  canSend?: boolean;
  onLimitReached?: () => void;
}

export function AnimatedInput({ onSend, disabled = false, canSend = true, onLimitReached }: AnimatedInputProps) {
  const [input, setInput] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
    }
  }, [input]);

  const handleSubmit = () => {
    if (!canSend) {
      onLimitReached?.();
      return;
    }

    if (input.trim() && !disabled) {
      onSend(input.trim());
      setInput('');
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
      }
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="p-0">
      <div className="flex items-center gap-2">
        <div 
          className={`flex-1 relative ${!canSend ? 'cursor-pointer' : ''}`}
          onClick={!canSend ? () => onLimitReached?.() : undefined}
        >
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={disabled || !canSend}
            placeholder={canSend ? "Ask about the uploaded PDF..." : "Sign up for unlimited prompts"}
            className={`w-full px-4 py-3 pr-24 border border-border rounded-xl resize-none focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-2 disabled:opacity-50 bg-muted/50 text-foreground placeholder:text-muted-foreground transition-all duration-200 max-h-32 custom-scroll ${!canSend ? 'cursor-pointer' : ''}`}
            rows={1}
          />
        </div>
        <motion.div
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
        >
          <Button
            onClick={handleSubmit}
            disabled={disabled || !input.trim() || !canSend}
            className="rounded-xl bg-accent px-5 py-3 text-accent-foreground hover:bg-accent/90"
          >
            <Send className="mr-2 h-4 w-4" />
            Send
          </Button>
        </motion.div>
      </div>
    </div>
  );
}
