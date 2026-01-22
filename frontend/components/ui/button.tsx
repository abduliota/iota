import React from 'react';

interface ButtonProps {
  children: React.ReactNode;
  onClick?: React.MouseEventHandler<HTMLButtonElement>;
  variant?: 'primary' | 'secondary' | 'ghost';
  disabled?: boolean;
  className?: string;
}

export function Button({ 
  children, 
  onClick, 
  variant = 'primary', 
  disabled = false,
  className = '' 
}: ButtonProps) {
  const baseStyles = 'px-4 py-2 rounded-lg font-medium transition-all duration-200 transform hover:scale-105 active:scale-95';
  const variants = {
    primary:
      'bg-blue-600 text-white hover:bg-blue-700 disabled:bg-gray-400 dark:bg-blue-500 dark:hover:bg-blue-600 shadow-md hover:shadow-lg hover:shadow-blue-300/50 dark:hover:shadow-blue-500/30',
    secondary:
      'bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-200 border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-600 shadow-md hover:shadow-lg hover:shadow-blue-200/50 dark:hover:shadow-blue-500/30 hover:border-blue-400 dark:hover:border-blue-500',
    ghost:
      'hover:bg-gray-100 text-gray-700 dark:hover:bg-gray-800 dark:text-gray-300 shadow-sm hover:shadow-md hover:shadow-blue-200/30 dark:hover:shadow-blue-500/20',
  };
  
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`${baseStyles} ${variants[variant]} ${className}`}
    >
      {children}
    </button>
  );
}
