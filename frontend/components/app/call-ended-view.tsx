'use client';

import React from 'react';
import { PhoneOff, RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface CallEndedViewProps {
  onRestartCall: () => void;
}

export const CallEndedView = ({ onRestartCall }: CallEndedViewProps) => {
  return (
    <section className="flex flex-col items-center justify-center p-6 text-center animate-in fade-in zoom-in-95 duration-300">
      {/* Icon */}
      <div className="mb-6 flex size-20 items-center justify-center rounded-full bg-zinc-500/10 text-zinc-400 ring-8 ring-zinc-500/5 dark:bg-zinc-800 dark:text-zinc-300">
        <PhoneOff className="size-9" />
      </div>

      {/* State Pill */}
      <div className="mb-3 inline-flex items-center gap-2 rounded-full border border-zinc-500/30 bg-zinc-500/10 px-3.5 py-1 text-xs font-semibold uppercase tracking-wider text-zinc-400">
        <span className="size-2 rounded-full bg-zinc-400" />
        State: Call Ended
      </div>

      {/* Headline */}
      <h2 className="text-2xl font-bold tracking-tight text-foreground md:text-3xl">
        Conversation Finished
      </h2>

      {/* Description */}
      <p className="mt-3 max-w-md text-sm leading-relaxed text-muted-foreground md:text-base">
        Your voice session with Local Commerce Assistant has ended. You can review the transcript or start a new call anytime.
      </p>

      {/* ONE Clear Primary Button to Start Again */}
      <Button
        size="lg"
        onClick={onRestartCall}
        className="mt-8 gap-2.5 rounded-full bg-primary px-8 py-6 text-sm font-semibold tracking-wide text-primary-foreground shadow-xl transition-all hover:scale-105 hover:bg-primary/90 focus:ring-4 focus:ring-primary/20"
      >
        <RefreshCw className="size-4" />
        Start New Call
      </Button>
    </section>
  );
};
