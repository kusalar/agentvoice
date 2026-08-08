import { useEffect, useRef, useState } from 'react';
import { ConnectionState } from 'livekit-client';
import { useAgent, useSessionContext } from '@livekit/components-react';

export type DisplayAgentState = 'ready' | 'connecting' | 'listening' | 'speaking' | 'ended';

export function useAgentState() {
  const session = useSessionContext();
  const agent = useAgent();
  const [hasStartedOnce, setHasStartedOnce] = useState(false);
  const [isManualEnded, setIsManualEnded] = useState(false);
  const wasConnectedRef = useRef(false);

  const isConnected = session.isConnected;
  const isConnecting = session.connectionState === ConnectionState.Connecting;
  const rawAgentState = agent.state; // 'disconnected' | 'connecting' | 'initializing' | 'listening' | 'thinking' | 'speaking' | 'failed'

  useEffect(() => {
    if (isConnected) {
      wasConnectedRef.current = true;
      setHasStartedOnce(true);
      setIsManualEnded(false);
    }
  }, [isConnected]);

  // Determine current 5-state lifecycle
  let displayState: DisplayAgentState = 'ready';

  if (isManualEnded) {
    displayState = 'ended';
  } else if (isConnecting || (hasStartedOnce && !isConnected && !wasConnectedRef.current)) {
    displayState = 'connecting';
  } else if (isConnected) {
    if (rawAgentState === 'speaking') {
      displayState = 'speaking';
    } else {
      // listening, thinking, initializing, or default while connected
      displayState = 'listening';
    }
  } else if (wasConnectedRef.current && !isConnected) {
    displayState = 'ended';
  } else {
    displayState = 'ready';
  }

  const startCall = async () => {
    setIsManualEnded(false);
    setHasStartedOnce(true);
    try {
      await session.start();
    } catch (err) {
      console.error('Error starting session:', err);
    }
  };

  const endCall = () => {
    setIsManualEnded(true);
    try {
      session.end();
    } catch (err) {
      console.error('Error ending session:', err);
    }
  };

  const resetToReady = () => {
    setIsManualEnded(false);
    setHasStartedOnce(false);
    wasConnectedRef.current = false;
  };

  return {
    displayState,
    rawAgentState,
    isConnected,
    isConnecting,
    startCall,
    endCall,
    resetToReady,
  };
}
