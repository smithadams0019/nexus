import { useCallback, useEffect, useRef, type RefObject } from 'react';

interface UseCameraReturn {
  startCamera: (facingMode: 'user' | 'environment') => Promise<void>;
  stopCamera: () => void;
  captureFrame: () => string | null;
  switchCamera: (facingMode: 'user' | 'environment') => Promise<void>;
  startScreenShare: () => Promise<void>;
}

export function useCamera(videoRef: RefObject<HTMLVideoElement>): UseCameraReturn {
  const streamRef = useRef<MediaStream | null>(null);

  const stopCamera = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
  }, [videoRef]);

  const startCamera = useCallback(async (facingMode: 'user' | 'environment') => {
    stopCamera();
    const stream = await navigator.mediaDevices.getUserMedia({
      video: {
        facingMode,
        width: { ideal: 1280 },
        height: { ideal: 720 },
      },
      audio: false,
    });
    streamRef.current = stream;
    if (videoRef.current) {
      videoRef.current.srcObject = stream;
    }
  }, [videoRef, stopCamera]);

  const captureFrame = useCallback((): string | null => {
    const video = videoRef.current;
    if (!video || video.readyState < 2) return null;

    const canvas = document.createElement('canvas');
    let width = video.videoWidth;
    let height = video.videoHeight;

    if (width > 1280) {
      const scale = 1280 / width;
      width = 1280;
      height = Math.round(height * scale);
    }

    canvas.width = width;
    canvas.height = height;
    const ctx = canvas.getContext('2d');
    if (!ctx) return null;

    ctx.drawImage(video, 0, 0, width, height);
    const dataUrl = canvas.toDataURL('image/jpeg', 0.7);
    return dataUrl.split(',')[1] || null;
  }, [videoRef]);

  const switchCamera = useCallback(async (facingMode: 'user' | 'environment') => {
    await startCamera(facingMode);
  }, [startCamera]);

  const startScreenShare = useCallback(async () => {
    stopCamera();
    const stream = await navigator.mediaDevices.getDisplayMedia({
      video: { width: { ideal: 1280 }, height: { ideal: 720 } },
      audio: false,
    });
    streamRef.current = stream;
    if (videoRef.current) {
      videoRef.current.srcObject = stream;
    }

    stream.getVideoTracks()[0].onended = () => {
      stopCamera();
    };
  }, [videoRef, stopCamera]);

  useEffect(() => {
    return () => {
      stopCamera();
    };
  }, [stopCamera]);

  return { startCamera, stopCamera, captureFrame, switchCamera, startScreenShare };
}
