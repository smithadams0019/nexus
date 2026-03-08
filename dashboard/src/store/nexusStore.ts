import { create } from 'zustand';
import { playAudioChunk, resetPlaybackSchedule } from '../lib/audioUtils';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: number;
}

interface Insight {
  id: string;
  title: string;
  content: string;
  category: 'anomaly' | 'insight' | 'suggestion' | 'warning';
  timestamp: number;
}

interface Alert {
  id: string;
  severity: 'info' | 'warning' | 'critical';
  message: string;
  timestamp: number;
}

interface NexusState {
  status: 'disconnected' | 'connecting' | 'connected';
  sessionId: string;
  ws: WebSocket | null;
  isStreaming: boolean;
  isMuted: boolean;
  cameraMode: 'user' | 'environment';
  mediaMode: 'camera' | 'screen';
  audioContext: AudioContext | null;
  isAiSpeaking: boolean;
  messages: Message[];
  insights: Insight[];
  alerts: Alert[];

  connect: () => void;
  disconnect: () => void;
  sendFrame: (frameData: string) => void;
  sendAudio: (audioData: string) => void;
  sendText: (text: string) => void;
  toggleMute: () => void;
  toggleCamera: () => void;
  switchMediaMode: (mode: 'camera' | 'screen') => void;
  setAudioContext: (ctx: AudioContext) => void;
  addMessage: (role: 'user' | 'assistant', content: string) => void;
  addInsight: (insight: Omit<Insight, 'id' | 'timestamp'>) => void;
  addAlert: (alert: Omit<Alert, 'id' | 'timestamp'>) => void;
  clearAlerts: () => void;
}

function generateId(): string {
  return Math.random().toString(16).slice(2, 10);
}

function getWsUrl(): string {
  const backendUrl = import.meta.env.VITE_BACKEND_URL;
  if (backendUrl) {
    return backendUrl.replace(/^http/, 'ws');
  }
  // In production, use the same host (wss:// for HTTPS, ws:// for HTTP)
  if (typeof window !== 'undefined' && window.location.hostname !== 'localhost') {
    const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    return `${proto}//${window.location.host}`;
  }
  return 'ws://localhost:8000';
}

export const useNexusStore = create<NexusState>((set, get) => ({
  status: 'disconnected',
  sessionId: '',
  ws: null,
  isStreaming: false,
  isMuted: false,
  cameraMode: 'user',
  mediaMode: 'camera',
  audioContext: null,
  isAiSpeaking: false,
  messages: [],
  insights: [],
  alerts: [],

  connect: () => {
    const sessionId = generateId();
    set({ status: 'connecting', sessionId });

    const wsUrl = `${getWsUrl()}/ws/${sessionId}`;
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      set({ status: 'connected', ws, isStreaming: true });
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        const state = get();

        switch (data.type) {
          case 'audio': {
            set({ isAiSpeaking: true });
            if (state.audioContext) {
              playAudioChunk(state.audioContext, data.data);
            }
            break;
          }
          case 'text': {
            get().addMessage('assistant', data.data);
            break;
          }
          case 'turn_complete': {
            set({ isAiSpeaking: false });
            resetPlaybackSchedule();
            break;
          }
          case 'insight': {
            get().addInsight({
              title: data.title || 'Insight',
              content: data.content || data.data,
              category: data.category || 'insight',
            });
            break;
          }
          case 'alert': {
            get().addAlert({
              severity: data.severity || 'info',
              message: data.message || data.data,
            });
            break;
          }
          case 'action_result': {
            const icon = data.success ? '✓' : '✗';
            get().addMessage('assistant', `${icon} Action: ${data.action} — ${data.message}`);
            break;
          }
        }
      } catch {
        // Ignore non-JSON messages
      }
    };

    ws.onclose = () => {
      set({
        status: 'disconnected',
        ws: null,
        isStreaming: false,
        isAiSpeaking: false,
      });
    };

    ws.onerror = () => {
      set({ status: 'disconnected', ws: null, isStreaming: false });
    };
  },

  disconnect: () => {
    const { ws } = get();
    if (ws) {
      ws.close();
    }
    set({
      status: 'disconnected',
      ws: null,
      isStreaming: false,
      isAiSpeaking: false,
      sessionId: '',
    });
  },

  sendFrame: (frameData: string) => {
    const { ws, status } = get();
    if (ws && status === 'connected') {
      ws.send(JSON.stringify({ type: 'frame', data: frameData }));
    }
  },

  sendAudio: (audioData: string) => {
    const { ws, status, isMuted } = get();
    if (ws && status === 'connected' && !isMuted) {
      ws.send(JSON.stringify({ type: 'audio', data: audioData }));
    }
  },

  sendText: (text: string) => {
    const { ws, status } = get();
    if (ws && status === 'connected' && text.trim()) {
      ws.send(JSON.stringify({ type: 'text', data: text.trim() }));
      get().addMessage('user', text.trim());
    }
  },

  toggleMute: () => {
    set((state) => ({ isMuted: !state.isMuted }));
  },

  toggleCamera: () => {
    set((state) => ({
      cameraMode: state.cameraMode === 'user' ? 'environment' : 'user',
    }));
  },

  switchMediaMode: (mode: 'camera' | 'screen') => {
    set({ mediaMode: mode });
  },

  setAudioContext: (ctx: AudioContext) => {
    set({ audioContext: ctx });
  },

  addMessage: (role: 'user' | 'assistant', content: string) => {
    set((state) => ({
      messages: [
        ...state.messages,
        {
          id: generateId(),
          role,
          content,
          timestamp: Date.now(),
        },
      ],
    }));
  },

  addInsight: (insight: Omit<Insight, 'id' | 'timestamp'>) => {
    set((state) => ({
      insights: [
        {
          id: generateId(),
          ...insight,
          timestamp: Date.now(),
        },
        ...state.insights,
      ],
    }));
  },

  addAlert: (alert: Omit<Alert, 'id' | 'timestamp'>) => {
    set((state) => ({
      alerts: [
        ...state.alerts,
        {
          id: generateId(),
          ...alert,
          timestamp: Date.now(),
        },
      ],
    }));
  },

  clearAlerts: () => {
    set({ alerts: [] });
  },
}));
