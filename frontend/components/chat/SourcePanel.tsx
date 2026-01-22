'use client';

import React from 'react';
import { Reference } from '@/lib/types';
import { Button } from '@/components/ui/button';

interface SourcePanelProps {
  sources: Reference[];
  isOpen: boolean;
  onClose: () => void;
}

export function SourcePanel({ sources, isOpen, onClose }: SourcePanelProps) {
  if (!isOpen) return null;

  return (
    <div className="w-80 border-l border-gray-700 bg-[#0a0a0a] p-4 overflow-y-auto transition-colors duration-200">
      <div className="flex justify-between items-center mb-4">
        <h3 className="font-semibold text-white">Sources</h3>
        <Button variant="ghost" onClick={onClose} className="text-xs">
          ✕
        </Button>
      </div>
      <div className="space-y-3">
        {sources.map((source) => (
          <div key={source.id} className="p-3 bg-gray-800 rounded-lg border border-gray-700 transition-colors duration-200">
            <div className="font-semibold text-sm text-white">{source.source}</div>
            <div className="text-xs text-gray-400 mt-1">Page {source.page}</div>
            <div className="text-xs text-gray-300 mt-2 line-clamp-3">{source.snippet}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
