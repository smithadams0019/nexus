import { useCallback, useEffect, useRef, useState } from 'react';

interface UseAudioReturn {
  startMic: (onAudioChunk: (base64: string) => void) => Promise<void>;
  stopMic: () => void;
  isMicActive: boolean;
}

function float32ToInt16Base64(float32: Float32Array): string {
  const int16 = new Int16Array(float32.length);
  for (let i = 0; i < float32.length; i++) {
    const s = Math.max(-1, Math.min(1, float32[i]));
    int16[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
  }

  const bytes = new Uint8Array(int16.buffer);
  let binary = '';
  for (let i = 0; i < bytes.length; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return btoa(binary);
}

export function useAudio(): UseAudioReturn {
  const [isMicActive, setIsMicActive] = useState(false);
  const streamRef = useRef<MediaStream | null>(null);
  const audioCtxRef = useRef<AudioContext | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const callbackRef = useRef<((base64: string) => void) | null>(null);

  const stopMic = useCallback(() => {
    if (processorRef.current) {
      processorRef.current.disconnect();
      processorRef.current = null;
    }
    if (audioCtxRef.current) {
      audioCtxRef.current.close();
      audioCtxRef.current = null;
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    callbackRef.current = null;
    setIsMicActive(false);
  }, []);

  const startMic = useCallback(async (onAudioChunk: (base64: string) => void) => {
    stopMic();
    callbackRef.current = onAudioChunk;

    const stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        sampleRate: 16000,
        channelCount: 1,
        echoCancellation: true,
        noiseSuppression: true,
      },
    });
    streamRef.current = stream;

    const audioCtx = new AudioContext({ sampleRate: 16000 });
    audioCtxRef.current = audioCtx;

    const source = audioCtx.createMediaStreamSource(stream);
    const processor = audioCtx.createScriptProcessor(4096, 1, 1);
    processorRef.current = processor;

    processor.onaudioprocess = (event) => {
      if (!callbackRef.current) return;
      const inputData = event.inputBuffer.getChannelData(0);
      const base64 = float32ToInt16Base64(new Float32Array(inputData));
      callbackRef.current(base64);
    };

    source.connect(processor);
    processor.connect(audioCtx.destination);
    setIsMicActive(true);
  }, [stopMic]);

  useEffect(() => {
    return () => {
      stopMic();
    };
  }, [stopMic]);

  return { startMic, stopMic, isMicActive };
}
