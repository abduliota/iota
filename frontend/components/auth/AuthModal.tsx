'use client';

import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Fingerprint } from 'lucide-react';

interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  onRegister: (email: string) => Promise<{ success: boolean; error?: string }>;
  onLogin: (email: string) => Promise<{ success: boolean; error?: string }>;
}

export function AuthModal({ isOpen, onClose, onSuccess, onRegister, onLogin }: AuthModalProps) {
  const [mode, setMode] = useState<'signup' | 'login'>('signup');
  const [email, setEmail] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim()) {
      setError('Please enter your email');
      return;
    }

    setIsLoading(true);
    setError('');

    const result = mode === 'signup' 
      ? await onRegister(email.trim())
      : await onLogin(email.trim());

    setIsLoading(false);

    if (result.success) {
      onSuccess();
      onClose();
      setEmail('');
    } else {
      setError(result.error || 'Authentication failed');
    }
  };

  return (
    <div className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-4">
      <div className="bg-[#1a1a1a] rounded-lg p-6 w-full max-w-md border border-gray-800">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-semibold text-white">
            {mode === 'signup' ? 'Sign Up' : 'Login'}
          </h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white transition-colors"
          >
            ✕
          </button>
        </div>

        <p className="text-sm text-gray-400 mb-6">
          {mode === 'signup'
            ? 'Create an account with fingerprint authentication for unlimited prompts'
            : 'Login with your fingerprint to access unlimited prompts'}
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Email
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="your@email.com"
              className="w-full px-4 py-2 bg-[#0a0a0a] border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
              disabled={isLoading}
            />
          </div>

          {error && (
            <div className="text-sm text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg p-3">
              {error}
            </div>
          )}

          <Button
            type="submit"
            disabled={isLoading || !email.trim()}
            className="w-full"
          >
            <Fingerprint className="h-4 w-4 mr-2" />
            {isLoading
              ? 'Processing...'
              : mode === 'signup'
              ? 'Sign Up with Fingerprint'
              : 'Login with Fingerprint'}
          </Button>
        </form>

        <div className="mt-4 text-center">
          <button
            onClick={() => {
              setMode(mode === 'signup' ? 'login' : 'signup');
              setError('');
            }}
            className="text-sm text-blue-400 hover:text-blue-300 transition-colors"
          >
            {mode === 'signup'
              ? 'Already have an account? Login'
              : "Don't have an account? Sign Up"}
          </button>
        </div>
      </div>
    </div>
  );
}
