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
    <div className="border-t border-gray-800 p-4 bg-[#0a0a0a]">
      <div className="flex items-end gap-2">
        <div className="flex-1 relative">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={disabled || !canSend}
            placeholder={canSend ? "Ask KSA regulatory questions..." : "Sign up for unlimited prompts"}
            className="w-full px-4 py-3 pr-12 border border-gray-700 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-800 bg-[#1a1a1a] text-white placeholder-gray-400 transition-all duration-200 max-h-32"
            rows={1}
          />
          <div className="absolute right-2 bottom-2 flex gap-1">
            <button className="p-1.5 text-gray-400 hover:text-white transition-colors">
              <Paperclip className="h-4 w-4" />
            </button>
            <button className="p-1.5 text-gray-400 hover:text-white transition-colors">
              <Mic className="h-4 w-4" />
            </button>
          </div>
        </div>
        <motion.div
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
        >
          <Button
            onClick={handleSubmit}
            disabled={disabled || !input.trim() || !canSend}
            className="px-6"
          >
            <Send className="h-4 w-4" />
          </Button>
        </motion.div>
      </div>
    </div>
  );
}
