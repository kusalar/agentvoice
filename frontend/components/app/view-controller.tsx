'use client';

import React from 'react';
import { useTheme } from 'next-themes';
import { AnimatePresence, motion } from 'motion/react';
import type { AppConfig } from '@/app-config';
import { AgentSessionView_01 } from '@/components/agents-ui/blocks/agent-session-view-01';
import { CallEndedView } from '@/components/app/call-ended-view';
import { ConnectingView } from '@/components/app/connecting-view';
import { MicPermissionModal } from '@/components/app/mic-permission-modal';
import { WelcomeView } from '@/components/app/welcome-view';
import { useAgentState } from '@/hooks/useAgentState';
import { useMicPermissions } from '@/hooks/useMicPermissions';

const MotionWelcomeView = motion.create(WelcomeView);
const MotionConnectingView = motion.create(ConnectingView);
const MotionSessionView = motion.create(AgentSessionView_01);
const MotionCallEndedView = motion.create(CallEndedView);

const VIEW_MOTION_PROPS = {
  variants: {
    visible: { opacity: 1, scale: 1 },
    hidden: { opacity: 0, scale: 0.98 },
  },
  initial: 'hidden',
  animate: 'visible',
  exit: 'hidden',
  transition: {
    duration: 0.3,
    ease: 'easeOut',
  },
};

interface ViewControllerProps {
  appConfig: AppConfig;
}

export function ViewController({ appConfig }: ViewControllerProps) {
  const { resolvedTheme } = useTheme();
  const { displayState, startCall, resetToReady } = useAgentState();
  const {
    hasError: hasMicError,
    errorMessage: micErrorMessage,
    errorType: micErrorType,
    requestMicAccess,
    handleDeviceError,
    clearError: clearMicError,
  } = useMicPermissions();

  const handleStartCall = async () => {
    clearMicError();
    const granted = await requestMicAccess();
    if (granted) {
      await startCall();
    }
  };

  const handleRestartCall = async () => {
    resetToReady();
    clearMicError();
    const granted = await requestMicAccess();
    if (granted) {
      await startCall();
    }
  };

  const handleRetryMicAccess = async () => {
    clearMicError();
    const granted = await requestMicAccess();
    if (granted && (displayState === 'ready' || displayState === 'ended')) {
      await startCall();
    }
  };

  return (
    <>
      {/* Microphone Permission Modal */}
      <MicPermissionModal
        isOpen={hasMicError}
        errorMessage={micErrorMessage}
        errorType={micErrorType}
        onRetry={handleRetryMicAccess}
        onClose={clearMicError}
      />

      <AnimatePresence mode="wait">
        {/* State 1: Ready — one clear button to begin */}
        {displayState === 'ready' && (
          <MotionWelcomeView
            key="welcome-ready"
            {...VIEW_MOTION_PROPS}
            startButtonText={appConfig.startButtonText || 'Start Conversation'}
            onStartCall={handleStartCall}
          />
        )}

        {/* State 2: Connecting — tell user to wait */}
        {displayState === 'connecting' && (
          <MotionConnectingView
            key="connecting"
            {...VIEW_MOTION_PROPS}
            message="Connecting to Local Commerce Assistant... Please wait a moment while we set up your audio session."
          />
        )}

        {/* State 3 & 4: Listening & Speaking — Active session with active speaker indicator */}
        {(displayState === 'listening' || displayState === 'speaking') && (
          <MotionSessionView
            key="session-active"
            {...VIEW_MOTION_PROPS}
            displayState={displayState}
            onDeviceError={(err) => handleDeviceError(err.error)}
            supportsChatInput={appConfig.supportsChatInput}
            supportsVideoInput={appConfig.supportsVideoInput}
            supportsScreenShare={appConfig.supportsScreenShare}
            isPreConnectBufferEnabled={appConfig.isPreConnectBufferEnabled}
            audioVisualizerType={appConfig.audioVisualizerType}
            audioVisualizerColor={
              resolvedTheme === 'dark'
                ? appConfig.audioVisualizerColorDark
                : appConfig.audioVisualizerColor
            }
            audioVisualizerColorShift={appConfig.audioVisualizerColorShift}
            audioVisualizerBarCount={appConfig.audioVisualizerBarCount}
            audioVisualizerGridRowCount={appConfig.audioVisualizerGridRowCount}
            audioVisualizerGridColumnCount={appConfig.audioVisualizerGridColumnCount}
            audioVisualizerRadialBarCount={appConfig.audioVisualizerRadialBarCount}
            audioVisualizerRadialRadius={appConfig.audioVisualizerRadialRadius}
            audioVisualizerWaveLineWidth={appConfig.audioVisualizerWaveLineWidth}
            className="fixed inset-0"
          />
        )}

        {/* State 5: Call ended — option to start again */}
        {displayState === 'ended' && (
          <MotionCallEndedView
            key="call-ended"
            {...VIEW_MOTION_PROPS}
            onRestartCall={handleRestartCall}
          />
        )}
      </AnimatePresence>
    </>
  );
}
