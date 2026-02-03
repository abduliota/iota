'use client';

import React from 'react';

interface PromptCounterProps {
  remaining: number;
  total: number;
  isAuthenticated: boolean;
}

export function PromptCounter({ remaining, total, isAuthenticated }: PromptCounterProps) {
  if (isAuthenticated) {
    return (
      <div className="unlimited-badge px-3 py-1 rounded-full text-xs font-medium bg-green-500/20 text-green-600 dark:bg-green-500/20 dark:text-green-400 transition-colors duration-200">
        Unlimited
      </div>
    );
  }

  const percentage = (remaining / total) * 100;
  const isWarning = remaining <= 2;

  return (
    <div className="flex items-center justify-center gap-2">
      <div className="text-xs text-muted-foreground">
        {remaining}/{total} prompts
      </div>
      <div className="w-20 h-1.5 rounded-full overflow-hidden bg-muted transition-colors duration-200">
        <div
          className={`h-full transition-all duration-300 ${
            isWarning ? 'bg-destructive' : 'bg-accent'
          }`}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
}
