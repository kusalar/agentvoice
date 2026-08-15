import { useCallback, useEffect, useState } from 'react';

export interface MicPermissionState {
  hasError: boolean;
  errorType: 'denied' | 'not_found' | 'in_use' | 'unknown' | null;
  errorMessage: string | null;
  permissionStatus: PermissionState | 'unknown';
}

export function useMicPermissions() {
  const [micState, setMicState] = useState<MicPermissionState>({
    hasError: false,
    errorType: null,
    errorMessage: null,
    permissionStatus: 'unknown',
  });

  const checkPermission = useCallback(async () => {
    if (typeof window === 'undefined' || !navigator?.permissions) return;
    try {
      // Permission API query for microphone
      const status = await navigator.permissions.query({ name: 'microphone' as PermissionName });
      setMicState((prev) => ({
        ...prev,
        permissionStatus: status.state,
        hasError: status.state === 'denied',
        errorType: status.state === 'denied' ? 'denied' : prev.errorType,
        errorMessage:
          status.state === 'denied'
            ? 'Microphone access is blocked by your browser settings.'
            : prev.errorMessage,
      }));

      status.onchange = () => {
        setMicState((prev) => ({
          ...prev,
          permissionStatus: status.state,
          hasError: status.state === 'denied',
          errorType: status.state === 'denied' ? 'denied' : status.state === 'granted' ? null : prev.errorType,
          errorMessage:
            status.state === 'denied'
              ? 'Microphone access is blocked by your browser settings.'
              : status.state === 'granted'
                ? null
                : prev.errorMessage,
        }));
      };
    } catch {
      // Browsers like Firefox may not support microphone permission query
    }
  }, []);

  useEffect(() => {
    checkPermission();
  }, [checkPermission]);

  const handleDeviceError = useCallback((error: Error | unknown) => {
    console.warn('Microphone device error captured:', error);
    const err = error instanceof Error ? error : new Error(String(error));
    const name = err.name || '';
    const message = err.message || '';

    let type: 'denied' | 'not_found' | 'in_use' | 'unknown' = 'unknown';
    let userMsg = 'Unable to access your microphone.';

    if (name === 'NotAllowedError' || name === 'PermissionDeniedError' || message.includes('Permission denied') || message.includes('NotAllowedError')) {
      type = 'denied';
      userMsg = 'Microphone permission was blocked. Please enable microphone access in your browser settings to continue.';
    } else if (name === 'NotFoundError' || name === 'DevicesNotFoundError') {
      type = 'not_found';
      userMsg = 'No microphone device was found on your system. Please connect a microphone and try again.';
    } else if (name === 'NotReadableError' || name === 'TrackStartError') {
      type = 'in_use';
      userMsg = 'Your microphone is currently in use by another application. Please close that app and try again.';
    }

    setMicState({
      hasError: true,
      errorType: type,
      errorMessage: userMsg,
      permissionStatus: type === 'denied' ? 'denied' : 'unknown',
    });
  }, []);

  const requestMicAccess = useCallback(async () => {
    if (typeof window === 'undefined' || !navigator?.mediaDevices) return false;
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      // Stop stream immediately after acquiring permission
      stream.getTracks().forEach((track) => track.stop());
      setMicState({
        hasError: false,
        errorType: null,
        errorMessage: null,
        permissionStatus: 'granted',
      });
      return true;
    } catch (err) {
      handleDeviceError(err);
      return false;
    }
  }, [handleDeviceError]);

  const clearError = useCallback(() => {
    setMicState((prev) => ({
      ...prev,
      hasError: false,
      errorType: null,
      errorMessage: null,
    }));
  }, []);

  return {
    ...micState,
    handleDeviceError,
    requestMicAccess,
    clearError,
    checkPermission,
  };
}
