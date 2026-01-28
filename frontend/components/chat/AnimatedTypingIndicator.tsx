'use client';

import React from 'react';
import { motion } from 'framer-motion';

export function AnimatedTypingIndicator() {
  return (
    <div className="flex justify-start mb-3">
      <div className="inline-flex items-center gap-1.5 rounded-2xl rounded-bl-sm bg-muted/70 px-3 py-2">
        {[0, 1, 2].map((i) => (
          <motion.div
            key={i}
            className="w-1.5 h-1.5 bg-muted-foreground/70 rounded-full"
            animate={{ y: [0, -3, 0], opacity: [0.4, 1, 0.4] }}
            transition={{
              duration: 0.6,
              repeat: Infinity,
              delay: i * 0.15,
              ease: 'easeInOut',
            }}
          />
        ))}
      </div>
    </div>
  );
}
