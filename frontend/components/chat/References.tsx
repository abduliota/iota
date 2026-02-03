'use client';

import React, { useState } from 'react';
import { Reference } from '@/lib/types';

interface ReferencesProps {
  references: Reference[];
}

export function References({ references }: ReferencesProps) {
  const [selectedIndex, setSelectedIndex] = useState(0);
  if (!references || references.length === 0) return null;

  const selected = references[selectedIndex];

  return (
    <div className="mt-2">
      <div className="flex flex-wrap gap-2 mb-2">
        {references.map((ref, i) => (
          <button
            key={ref.id}
            type="button"
            onClick={() => setSelectedIndex(i)}
            className={`text-xs px-2 py-1 rounded-full border transition-colors ${
              i === selectedIndex
                ? 'bg-muted text-foreground border-border'
                : 'bg-background/60 text-muted-foreground border-border hover:text-foreground'
            }`}
          >
            Page {ref.page}
          </button>
        ))}
      </div>
      <div className="p-3 rounded-lg border border-border bg-background/60 text-xs">
        <div className="font-semibold text-foreground">
          {selected.source}
        </div>
        <div className="text-muted-foreground mt-0.5">
          Page {selected.page}
        </div>
        <div className="text-muted-foreground mt-1 whitespace-pre-wrap break-words">
          {selected.snippet}
        </div>
      </div>
    </div>
  );
}
