'use client';

import React from 'react';
import { Bot, Mic, Radio, Volume2 } from 'lucide-react';
import { motion } from 'motion/react';
import type { DisplayAgentState } from '@/hooks/useAgentState';

interface SpeakerIndicatorProps {
  state: DisplayAgentState;
  className?: string;
}

export function SpeakerIndicator({ state, className = '' }: SpeakerIndicatorProps) {
  return (
    <div
      className={`relative flex flex-col items-center justify-center gap-2 rounded-2xl border border-border/40 bg-card/60 p-4 shadow-lg backdrop-blur-md transition-all duration-300 ${className}`}
    >
      {/* State: Ready */}
      {state === 'ready' && (
        <div className="flex items-center gap-3">
          <div className="flex size-8 items-center justify-center rounded-full bg-emerald-500/10 text-emerald-500 ring-4 ring-emerald-500/10">
            <Radio className="size-4 animate-pulse" />
          </div>
          <div className="text-left">
            <p className="text-xs font-semibold uppercase tracking-wider text-emerald-500">
              Status: Ready
            </p>
            <p className="text-sm font-medium text-foreground">Click start button to begin conversation</p>
          </div>
        </div>
      )}

      {/* State: Connecting */}
      {state === 'connecting' && (
        <div className="flex items-center gap-3">
          <div className="flex size-8 items-center justify-center rounded-full bg-amber-500/10 text-amber-500 ring-4 ring-amber-500/10">
            <Radio className="size-4 animate-spin" />
          </div>
          <div className="text-left">
            <p className="text-xs font-semibold uppercase tracking-wider text-amber-500">
              Status: Connecting
            </p>
            <p className="text-sm font-medium text-foreground">Joining call, please wait a moment...</p>
          </div>
        </div>
      )}

      {/* State: Listening (User Speaking / Listening to User) */}
      {state === 'listening' && (
        <div className="flex w-full flex-col items-center justify-center gap-2 sm:flex-row sm:justify-between">
          <div className="flex items-center gap-3">
            <div className="relative flex size-9 items-center justify-center rounded-full bg-cyan-500/15 text-cyan-400 ring-4 ring-cyan-500/10">
              <Mic className="size-5" />
              <span className="absolute -top-0.5 -right-0.5 flex size-3">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-cyan-400 opacity-75"></span>
                <span className="relative inline-flex size-3 rounded-full bg-cyan-500"></span>
              </span>
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="rounded bg-cyan-500/20 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-cyan-400">
                  User Active
                </span>
                <span className="text-xs font-semibold text-cyan-500 dark:text-cyan-400">Listening to you</span>
              </div>
              <p className="text-xs text-muted-foreground">The agent is active and listening to your voice</p>
            </div>
          </div>

          {/* User Volume Bar Indicator */}
          <div className="flex items-center gap-1 rounded-full bg-muted/60 px-3 py-1.5 border border-cyan-500/20">
            <Volume2 className="size-4 text-cyan-400" />
            <div className="flex items-end gap-1 h-4">
              {[0.4, 0.8, 0.5, 1, 0.6, 0.9, 0.3].map((heightScale, i) => (
                <motion.span
                  key={i}
                  className="w-1 rounded-full bg-cyan-400"
                  animate={{
                    height: ['20%', `${heightScale * 100}%`, '20%'],
                  }}
                  transition={{
                    duration: 0.8,
                    repeat: Infinity,
                    repeatType: 'reverse',
                    delay: i * 0.1,
                  }}
                />
              ))}
            </div>
          </div>
        </div>
      )}

      {/* State: Speaking (Agent Speaking to User) */}
      {state === 'speaking' && (
        <div className="flex w-full flex-col items-center justify-center gap-2 sm:flex-row sm:justify-between">
          <div className="flex items-center gap-3">
            <div className="relative flex size-9 items-center justify-center rounded-full bg-indigo-500/15 text-indigo-400 ring-4 ring-indigo-500/10">
              <Bot className="size-5 animate-bounce-short" />
              <span className="absolute -top-0.5 -right-0.5 flex size-3">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-indigo-400 opacity-75"></span>
                <span className="relative inline-flex size-3 rounded-full bg-indigo-500"></span>
              </span>
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="rounded bg-indigo-500/20 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-indigo-400">
                  Agent Active
                </span>
                <span className="text-xs font-semibold text-indigo-500 dark:text-indigo-400">Agent is speaking</span>
              </div>
              <p className="text-xs text-muted-foreground">Local Commerce Assistant is replying to you</p>
            </div>
          </div>

          {/* Agent Waveform Indicator */}
          <div className="flex items-center gap-1.5 rounded-full bg-indigo-950/40 px-3 py-1.5 border border-indigo-500/30">
            <div className="flex items-center gap-1 h-5">
              {[0.3, 0.9, 0.6, 1, 0.7, 0.95, 0.4, 0.8].map((scale, i) => (
                <motion.span
                  key={i}
                  className="w-1.5 rounded-full bg-gradient-to-t from-indigo-500 via-purple-400 to-pink-400"
                  animate={{
                    height: ['30%', `${scale * 100}%`, '20%'],
                  }}
                  transition={{
                    duration: 0.6,
                    repeat: Infinity,
                    repeatType: 'mirror',
                    delay: i * 0.08,
                  }}
                />
              ))}
            </div>
          </div>
        </div>
      )}

      {/* State: Call Ended */}
      {state === 'ended' && (
        <div className="flex items-center gap-3">
          <div className="flex size-8 items-center justify-center rounded-full bg-zinc-500/10 text-zinc-400 ring-4 ring-zinc-500/10">
            <Radio className="size-4 opacity-50" />
          </div>
          <div className="text-left">
            <p className="text-xs font-semibold uppercase tracking-wider text-zinc-400">
              Status: Call Ended
            </p>
            <p className="text-sm font-medium text-foreground">The conversation is over. Start again whenever you wish.</p>
          </div>
        </div>
      )}
    </div>
  );
}
