'use client';

import React from 'react';

function ThemeToggle() {
  const toggle = () => {
    document.documentElement.classList.toggle('dark');
  };
  return (
    <button
      type="button"
      onClick={toggle}
      className="rounded-full bg-muted px-3 py-1 text-xs font-medium text-muted-foreground hover:text-foreground transition-colors"
      aria-label="Toggle light/dark mode"
    >
      Theme
    </button>
  );
}

export function SummaryCard() {
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
        <ThemeToggle />
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        <span className="rounded-full bg-green-500/10 px-3 py-1 text-xs font-medium text-green-600 dark:text-green-400">
          Live · API healthy
        </span>
        <span className="rounded-full bg-muted px-3 py-1 text-xs font-medium text-muted-foreground">
          Azure Search
        </span>
        <span className="rounded-full bg-muted px-3 py-1 text-xs font-medium text-muted-foreground">
          RAG
        </span>
      </div>
      <div className="mt-6 grid grid-cols-3 gap-4 border-t border-border pt-4">
        <div>
          <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
            Docs Ingested
          </p>
          <p className="mt-1 text-xl font-semibold text-foreground">9</p>
        </div>
        <div>
          <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
            Chunks
          </p>
          <p className="mt-1 text-xl font-semibold text-foreground">884</p>
        </div>
        <div>
          <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
            Q&A Pairs
          </p>
          <p className="mt-1 text-xl font-semibold text-foreground">0</p>
        </div>
      </div>
    </div>
  );
}
