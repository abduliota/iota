'use client';

import React from 'react';
import { ThemeToggle } from '@/components/ui/ThemeToggle';

interface SummaryCardProps {
  rightSlot?: React.ReactNode;
}

export function SummaryCard({ rightSlot }: SummaryCardProps) {
  return (
    <div className="rounded-xl border border-border bg-card p-6 shadow-sm transition-colors duration-200">
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
            IOTA KSA
          </p>
      <div className="mt-2 flex items-center gap-2">
        <div className="h-8 w-1 rounded-full bg-accent" />
        <h1 className="text-2xl font-semibold text-foreground">
          Regulation AI
        </h1>
      </div>
          <p className="mt-2 text-sm text-muted-foreground">
            AI answers with citations from SAMA rulebooks and schemes.
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          {rightSlot != null ? (
            <div className="hidden md:block">{rightSlot}</div>
          ) : null}
          <ThemeToggle />
        </div>
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        <span className="rounded-full bg-green-500/10 px-3 py-1 text-xs font-medium text-green-600 dark:text-green-400">
          Live · API healthy
        </span>
        <span className="rounded-full bg-muted px-3 py-1 text-xs font-medium text-muted-foreground">
          IOTA-Qwen7B
        </span>
        <span className="rounded-full bg-muted px-3 py-1 text-xs font-medium text-muted-foreground">
          Multi-Agent Architecture
        </span>
        <span className="rounded-full bg-muted px-3 py-1 text-xs font-medium text-muted-foreground">
          RAG
        </span>
      </div>
    </div>
  );
}
