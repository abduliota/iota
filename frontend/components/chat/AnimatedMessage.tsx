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
      initial={
        isUser
          ? { opacity: 0, x: 16 }
          : { opacity: 0, y: 4 }
      }
      animate={{ opacity: 1, x: 0, y: 0 }}
      transition={{
        duration: 0.18,
        ease: 'easeOut',
        delay: Math.min(index * 0.03, 0.3),
      }}
    >
      <MessageBubble message={message} />
    </motion.div>
  );
}
