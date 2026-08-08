'use client';

import React from 'react';
import { Loader2, Radio } from 'lucide-react';
import { motion } from 'motion/react';

interface ConnectingViewProps {
  message?: string;
}

export const ConnectingView = ({
  message = 'Connecting to Local Commerce Assistant... Please wait a moment.',
}: ConnectingViewProps) => {
  return (
    <section className="flex flex-col items-center justify-center p-6 text-center animate-in fade-in zoom-in-95 duration-300">
      {/* Animated Orb Graphic */}
      <div className="relative mb-8 flex items-center justify-center">
        <motion.div
          className="absolute size-36 rounded-full bg-gradient-to-tr from-indigo-500/20 via-purple-500/20 to-pink-500/20 blur-xl"
          animate={{
            scale: [1, 1.25, 1],
            opacity: [0.5, 0.8, 0.5],
          }}
          transition={{
            duration: 2,
            repeat: Infinity,
            ease: 'easeInOut',
          }}
        />

        <motion.div
          className="absolute size-28 rounded-full border-2 border-indigo-500/40 border-t-indigo-500"
          animate={{ rotate: 360 }}
          transition={{
            duration: 1.5,
            repeat: Infinity,
            ease: 'linear',
          }}
        />

        <div className="relative flex size-20 items-center justify-center rounded-full bg-indigo-600/10 text-indigo-500 shadow-inner ring-8 ring-indigo-500/10 dark:bg-indigo-500/20 dark:text-indigo-400">
          <Radio className="size-8 animate-pulse" />
        </div>
      </div>

      {/* State Headline */}
      <div className="inline-flex items-center gap-2 rounded-full border border-amber-500/30 bg-amber-500/10 px-3 py-1 text-xs font-semibold uppercase tracking-wider text-amber-500 mb-3">
        <Loader2 className="size-3.5 animate-spin" />
        State: Connecting
      </div>

      <h2 className="text-2xl font-bold tracking-tight text-foreground md:text-3xl">
        Joining Voice Session
      </h2>

      {/* User instruction */}
      <p className="mt-3 max-w-md text-sm leading-relaxed text-muted-foreground md:text-base">
        {message}
      </p>

      {/* Status Bar */}
      <div className="mt-6 flex items-center gap-2 text-xs font-medium text-muted-foreground/80">
        <span className="size-2 rounded-full bg-amber-400 animate-ping" />
        Establishing secure WebRTC connection...
      </div>
    </section>
  );
};
