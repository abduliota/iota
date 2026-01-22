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
      <div className="px-3 py-1 bg-green-500/20 text-green-400 rounded-full text-xs font-medium">
        Unlimited
      </div>
    );
  }

  const percentage = (remaining / total) * 100;
  const isWarning = remaining <= 2;

  return (
    <div className="flex items-center gap-2">
      <div className="text-xs text-gray-400">
        {remaining}/{total} prompts
      </div>
      <div className="w-20 h-1.5 bg-gray-800 rounded-full overflow-hidden">
        <div
          className={`h-full transition-all duration-300 ${
            isWarning ? 'bg-red-500' : 'bg-blue-500'
          }`}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
}
