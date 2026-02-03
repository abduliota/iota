'use client';

import React from 'react';
import { Reference } from '@/lib/types';

interface LatestSourcesPanelProps {
  references?: Reference[] | null;
}

export function LatestSourcesPanel({ references }: LatestSourcesPanelProps) {
  const hasRefs = references && references.length > 0;

  return (
    <div className="flex flex-col flex-1 min-h-0 rounded-xl border border-border bg-card p-4 transition-colors duration-200 md:p-5">
      <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
        Latest Sources
      </p>
      <h3 className="mt-1 text-sm font-semibold text-foreground">
        Context spotlight
      </h3>
      {hasRefs ? (
        <div className="mt-3 flex-1 min-h-0 overflow-y-auto custom-scroll">
          <div className="space-y-2">
            {references!.map((ref) => (
              <div
                key={ref.id}
                className="rounded-lg border border-border bg-muted/30 p-3 text-xs"
              >
                <p className="font-medium text-foreground">{ref.source}</p>
                <p className="mt-0.5 text-muted-foreground">Page {ref.page}</p>
                <p className="mt-1 line-clamp-3 text-muted-foreground">
                  {ref.snippet}
                </p>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <p className="mt-3 text-sm text-muted-foreground">
          Ask a question to see cited passages.
        </p>
      )}
    </div>
  );
}
