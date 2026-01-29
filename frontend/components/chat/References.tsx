import React from 'react';
import { Reference } from '@/lib/types';

interface ReferencesProps {
  references: Reference[];
}

export function References({ references }: ReferencesProps) {
  if (!references || references.length === 0) return null;

  return (
    <div className="mt-2 space-y-2">
      {references.map((ref) => (
        <div
          key={ref.id}
          className="p-3 rounded-lg border border-border bg-background/60 text-xs"
        >
          <div className="font-semibold text-foreground">
            {ref.source}
          </div>
          <div className="text-muted-foreground mt-0.5">
            Page {ref.page}
          </div>
          <div className="text-muted-foreground mt-1 line-clamp-3">
            {ref.snippet}
          </div>
        </div>
      ))}
    </div>
  );
}
