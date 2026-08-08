'use client';

import React from 'react';
import { AlertTriangle, CheckCircle2, MicOff, RefreshCw, X } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface MicPermissionModalProps {
  isOpen: boolean;
  errorMessage?: string | null;
  errorType?: 'denied' | 'not_found' | 'in_use' | 'unknown' | null;
  onRetry: () => void;
  onClose: () => void;
}

export function MicPermissionModal({
  isOpen,
  errorMessage,
  errorType = 'denied',
  onRetry,
  onClose,
}: MicPermissionModalProps) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="relative w-full max-w-lg overflow-hidden rounded-2xl border border-red-500/20 bg-background/95 p-6 shadow-2xl backdrop-blur-md dark:bg-zinc-900/95 md:p-8">
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 rounded-full p-1.5 text-muted-foreground transition-colors hover:bg-zinc-800 hover:text-foreground"
          aria-label="Close dialog"
        >
          <X className="size-5" />
        </button>

        {/* Header Icon */}
        <div className="mx-auto mb-4 flex size-14 items-center justify-center rounded-2xl bg-red-500/10 text-red-500 ring-8 ring-red-500/5">
          <MicOff className="size-7" />
        </div>

        {/* Title */}
        <h3 className="text-center text-xl font-bold tracking-tight text-foreground md:text-2xl">
          Microphone Access Blocked
        </h3>

        {/* Main Message */}
        <p className="mt-2 text-center text-sm leading-relaxed text-muted-foreground">
          {errorMessage ||
            'Your browser blocked access to the microphone. The voice assistant needs microphone access to listen and speak with you.'}
        </p>

        {/* Detailed Instructions if Permission Denied */}
        {errorType === 'denied' && (
          <div className="mt-6 rounded-xl border border-border/60 bg-muted/40 p-4 text-left">
            <h4 className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-foreground">
              <AlertTriangle className="size-4 text-amber-500" />
              How to enable your microphone:
            </h4>
            <ol className="mt-3 space-y-2.5 text-xs leading-5 text-muted-foreground">
              <li className="flex items-start gap-2">
                <span className="flex size-5 shrink-0 items-center justify-center rounded-full bg-primary/10 text-[11px] font-bold text-primary">
                  1
                </span>
                <span>
                  Look for the <strong className="text-foreground">Lock (🔒) or Control icon</strong> next to the URL address bar at the top of your browser.
                </span>
              </li>
              <li className="flex items-start gap-2">
                <span className="flex size-5 shrink-0 items-center justify-center rounded-full bg-primary/10 text-[11px] font-bold text-primary">
                  2
                </span>
                <span>
                  Click it and set <strong className="text-foreground">Microphone</strong> permission to <strong className="text-emerald-500">"Allow"</strong>.
                </span>
              </li>
              <li className="flex items-start gap-2">
                <span className="flex size-5 shrink-0 items-center justify-center rounded-full bg-primary/10 text-[11px] font-bold text-primary">
                  3
                </span>
                <span>
                  Click <strong className="text-foreground">"Retry Microphone Access"</strong> below to start talking.
                </span>
              </li>
            </ol>
          </div>
        )}

        {/* Action Buttons */}
        <div className="mt-6 flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
          <Button
            variant="outline"
            onClick={onClose}
            className="w-full rounded-full border-border/80 sm:w-auto"
          >
            Dismiss
          </Button>
          <Button
            onClick={onRetry}
            className="w-full gap-2 rounded-full bg-primary font-medium text-primary-foreground shadow-lg hover:bg-primary/90 sm:w-auto"
          >
            <RefreshCw className="size-4 animate-spin-slow" />
            Retry Microphone Access
          </Button>
        </div>
      </div>
    </div>
  );
}
