import { useState, useEffect } from 'react';

const PROMPT_LIMIT = 10;
const STORAGE_KEY = 'ksa_regtech_prompt_count';
const RESET_TIME_KEY = 'ksa_regtech_reset_time';

export function usePromptLimit() {
  const [remainingPrompts, setRemainingPrompts] = useState(PROMPT_LIMIT);
  const [canSend, setCanSend] = useState(true);

  useEffect(() => {
    loadPromptCount();
  }, []);

  const loadPromptCount = () => {
    if (typeof window === 'undefined') return;
    
    const count = parseInt(localStorage.getItem(STORAGE_KEY) || '0', 10);
    const resetTime = localStorage.getItem(RESET_TIME_KEY);
    const now = new Date().getTime();
    
    if (resetTime && now > parseInt(resetTime, 10)) {
      resetPrompts();
    } else {
      const remaining = Math.max(0, PROMPT_LIMIT - count);
      setRemainingPrompts(remaining);
      setCanSend(remaining > 0);
    }
  };

  const incrementPrompt = () => {
    if (typeof window === 'undefined') return;
    
    const count = parseInt(localStorage.getItem(STORAGE_KEY) || '0', 10);
    const newCount = count + 1;
    localStorage.setItem(STORAGE_KEY, newCount.toString());
    
    if (count === 0) {
      const resetTime = new Date().getTime() + 24 * 60 * 60 * 1000;
      localStorage.setItem(RESET_TIME_KEY, resetTime.toString());
    }
    
    const remaining = Math.max(0, PROMPT_LIMIT - newCount);
    setRemainingPrompts(remaining);
    setCanSend(remaining > 0);
  };

  const resetPrompts = () => {
    if (typeof window === 'undefined') return;
    localStorage.removeItem(STORAGE_KEY);
    localStorage.removeItem(RESET_TIME_KEY);
    setRemainingPrompts(PROMPT_LIMIT);
    setCanSend(true);
  };

  return { remainingPrompts, canSend, incrementPrompt, resetPrompts };
}
