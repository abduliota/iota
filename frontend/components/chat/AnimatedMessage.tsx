'use client';

import React from 'react';
import { motion } from 'framer-motion';
import { MessageBubble } from './MessageBubble';
import { Message } from '@/lib/types';

interface AnimatedMessageProps {
  message: Message;
  index: number;
}

export function AnimatedMessage({ message, index }: AnimatedMessageProps) {
  const isUser = message.role === 'user';

  return (
    <motion.div
      initial={{ opacity: 0, x: isUser ? 20 : -20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.3, delay: index * 0.05 }}
    >
      <MessageBubble message={message} />
    </motion.div>
  );
}
