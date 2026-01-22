'use client';

import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';

export function IngestCard() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [status, setStatus] = useState<'idle' | 'success'>('idle');
  const [sessionUploads, setSessionUploads] = useState<string[]>([]);
  const [indexedDocs] = useState([
    { name: 'Account Opening Rules | SAMA Rulebook.pdf', chunks: 385, pages: 144 },
    { name: 'GDBC-381000095091-1438H.pdf', chunks: 2, pages: 1 },
    { name: 'Guideline for National Overall Reference Architecture (NORA)- V1.0.pdf', chunks: 95, pages: 54 },
  ]);

  const handleUpload = () => {
    if (!selectedFile) return;
    setUploading(true);
    setTimeout(() => {
      setSessionUploads((prev) => [...prev, selectedFile.name]);
      setStatus('success');
      setUploading(false);
    }, 800);
  };

  return (
    <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-4 bg-white dark:bg-gray-800 shadow-md mb-4">
      <div className="mb-4">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-1">Upload regulator PDFs</h3>
        <p className="text-sm text-gray-600 dark:text-gray-400">
          Mock-only: select a PDF and click upload to see status.
        </p>
      </div>

      <div className="space-y-2 mb-4">
        <label htmlFor="pdf-upload" className="block text-sm font-medium text-gray-700 dark:text-gray-300">Upload PDF</label>
        <input
          id="pdf-upload"
          type="file"
          accept="application/pdf"
          onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
          aria-label="Upload PDF file"
          className="block w-full text-sm text-gray-700 dark:text-gray-200 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100 dark:file:bg-gray-700 dark:file:text-blue-400"
        />
        <Button onClick={handleUpload} disabled={!selectedFile || uploading}>
          {uploading ? 'Uploading…' : 'Upload & Index'}
        </Button>
      </div>

      {status === 'success' && (
        <div className="mb-4 text-sm text-green-600 dark:text-green-400 font-medium">
          Indexed 2 chunks (mock).
        </div>
      )}

      {sessionUploads.length > 0 && (
        <div className="mb-4 text-sm text-gray-800 dark:text-gray-200">
          <strong className="font-semibold">Uploaded this session:</strong>
          <ul className="list-disc list-inside mt-1 space-y-1">
            {sessionUploads.map((name, idx) => (
              <li key={idx}>{name}</li>
            ))}
          </ul>
        </div>
      )}

      <div className="space-y-2">
        <p className="text-sm font-medium text-gray-700 dark:text-gray-300">Indexed documents (mock)</p>
        <ul className="space-y-2 text-sm">
          {indexedDocs.map((doc, idx) => (
            <li key={idx} className="flex justify-between items-center text-gray-800 dark:text-gray-200">
              <span className="truncate mr-2">{doc.name}</span>
              <span className="text-xs text-gray-500 dark:text-gray-400 whitespace-nowrap">
                {doc.chunks} chunks · {doc.pages} pages
              </span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
