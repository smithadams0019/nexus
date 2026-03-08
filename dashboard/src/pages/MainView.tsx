import { useCallback, useEffect, useRef } from 'react';
import { Eye, Zap } from 'lucide-react';
import { useNexusStore } from '../store/nexusStore';
import { useCamera } from '../hooks/useCamera';
import { useAudio } from '../hooks/useAudio';
import { createAudioContext } from '../lib/audioUtils';
import { CameraView } from '../components/CameraView';
import { Controls } from '../components/Controls';
import { ConversationLog } from '../components/ConversationLog';
import { InsightCards } from '../components/InsightCards';
import { AlertPanel } from '../components/AlertPanel';
import { StatusBar } from '../components/StatusBar';
import { TextInput } from '../components/TextInput';

export function MainView() {
  const videoRef = useRef<HTMLVideoElement>(null!);
  const frameIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const {
    status,
    sessionId,
    isStreaming,
    isMuted,
    cameraMode,
    mediaMode,
    isAiSpeaking,
    messages,
    insights,
    alerts,
    connect,
    disconnect,
    sendFrame,
    sendAudio,
    sendText,
    toggleMute,
    toggleCamera,
    switchMediaMode,
    setAudioContext,
  } = useNexusStore();

  const { startCamera, stopCamera, captureFrame, switchCamera, startScreenShare } =
    useCamera(videoRef);
  const { startMic, stopMic } = useAudio();

  const handleDismissAlert = useCallback(
    (id: string) => {
      const store = useNexusStore.getState();
      const filtered = store.alerts.filter((a) => a.id !== id);
      useNexusStore.setState({ alerts: filtered });
    },
    [],
  );

  // Start camera and mic when connected
  useEffect(() => {
    if (status === 'connected') {
      const ctx = createAudioContext();
      setAudioContext(ctx);

      startCamera(cameraMode);
      startMic((audioData) => {
        sendAudio(audioData);
      });

      // Send video frames every 1 second
      frameIntervalRef.current = setInterval(() => {
        const frame = captureFrame();
        if (frame) {
          sendFrame(frame);
        }
      }, 1000);

      return () => {
        if (frameIntervalRef.current) {
          clearInterval(frameIntervalRef.current);
          frameIntervalRef.current = null;
        }
      };
    } else {
      stopCamera();
      stopMic();
      if (frameIntervalRef.current) {
        clearInterval(frameIntervalRef.current);
        frameIntervalRef.current = null;
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status]);

  // Handle camera mode switch
  useEffect(() => {
    if (status === 'connected' && mediaMode === 'camera') {
      switchCamera(cameraMode);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cameraMode]);

  const handleSwitchCamera = () => {
    toggleCamera();
  };

  const handleToggleScreenShare = async () => {
    if (mediaMode === 'screen') {
      switchMediaMode('camera');
      await startCamera(cameraMode);
    } else {
      switchMediaMode('screen');
      try {
        await startScreenShare();
      } catch {
        switchMediaMode('camera');
        await startCamera(cameraMode);
      }
    }
  };

  const handleDisconnect = () => {
    stopCamera();
    stopMic();
    disconnect();
  };

  const handleConnect = () => {
    connect();
  };

  // Disconnected landing screen
  if (status === 'disconnected') {
    return (
      <div className="h-full flex flex-col items-center justify-center px-6">
        <div className="flex flex-col items-center max-w-sm w-full">
          {/* Logo */}
          <div className="w-20 h-20 rounded-2xl bg-nexus-primary/10 border border-nexus-primary/20 flex items-center justify-center mb-6">
            <Eye className="w-10 h-10 text-nexus-primary" />
          </div>

          <h1 className="text-3xl font-bold text-white mb-2 tracking-tight">Nexus</h1>
          <p className="text-sm text-white/40 text-center mb-8 leading-relaxed">
            Voice + Vision AI Copilot. Point your camera at anything and talk to get instant AI
            insights.
          </p>

          {/* Feature pills */}
          <div className="flex flex-wrap gap-2 justify-center mb-8">
            {['Real-time Vision', 'Voice Chat', 'Smart Insights', 'Alerts'].map((f) => (
              <span
                key={f}
                className="text-xs px-3 py-1.5 rounded-full bg-nexus-surface border border-nexus-border text-white/50"
              >
                {f}
              </span>
            ))}
          </div>

          {/* Connect button */}
          <button
            onClick={handleConnect}
            className="w-full py-3.5 rounded-xl bg-nexus-primary hover:bg-nexus-primary/80 text-white font-semibold text-sm transition-colors flex items-center justify-center gap-2"
          >
            <Zap className="w-4 h-4" />
            Start Session
          </button>

          <p className="text-[10px] text-white/20 mt-4 text-center">
            Requires camera and microphone access
          </p>
        </div>
      </div>
    );
  }

  // Connected view
  return (
    <div className="h-full flex flex-col md:flex-row">
      <AlertPanel alerts={alerts} onDismiss={handleDismissAlert} />

      {/* Camera area */}
      <div className="h-[55vh] md:h-full md:flex-1 relative shrink-0">
        <CameraView videoRef={videoRef} status={status} isAiSpeaking={isAiSpeaking}>
          <Controls
            isMuted={isMuted}
            mediaMode={mediaMode}
            onToggleMute={toggleMute}
            onSwitchCamera={handleSwitchCamera}
            onToggleScreenShare={handleToggleScreenShare}
            onDisconnect={handleDisconnect}
          />
        </CameraView>
      </div>

      {/* Sidebar / bottom panel */}
      <div className="flex-1 md:w-80 md:flex-none flex flex-col bg-nexus-dark border-t md:border-t-0 md:border-l border-nexus-border overflow-hidden">
        <StatusBar status={status} sessionId={sessionId} isStreaming={isStreaming} />

        {/* Tabs area with conversation and insights */}
        <div className="flex-1 flex flex-col overflow-hidden">
          <ConversationLog messages={messages} />

          {/* Insights section */}
          {insights.length > 0 && (
            <div className="border-t border-nexus-border px-3 py-2 shrink-0">
              <h3 className="text-[10px] uppercase tracking-wider text-white/30 font-semibold mb-2">
                Insights
              </h3>
              <InsightCards insights={insights} />
            </div>
          )}
        </div>

        <TextInput onSend={sendText} disabled={status !== 'connected'} />
      </div>
    </div>
  );
}
