import React, { useState } from 'react';
import { Reference } from '@/lib/types';

interface ReferencesProps {
  references: Reference[];
}

export function References({ references }: ReferencesProps) {
  const [hoveredRef, setHoveredRef] = useState<string | null>(null);

  if (!references || references.length === 0) return null;

  return (
    <div className="mt-2 flex flex-wrap gap-2">
      {references.map((ref, index) => (
        <div key={ref.id} className="relative">
          <button
            onMouseEnter={() => setHoveredRef(ref.id)}
            onMouseLeave={() => setHoveredRef(null)}
            className="text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 underline text-sm transition-colors duration-200"
          >
            {index + 1}
          </button>
          {hoveredRef === ref.id && (
            <div className="absolute bottom-full left-0 mb-2 w-64 p-3 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg shadow-lg z-10 transition-colors duration-200">
              <div className="font-semibold text-sm dark:text-white">{ref.source}</div>
              <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">Page {ref.page}</div>
              <div className="text-xs text-gray-600 dark:text-gray-300 mt-2 line-clamp-3">{ref.snippet}</div>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
