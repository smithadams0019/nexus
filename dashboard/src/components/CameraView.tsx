import { type RefObject } from 'react';

interface CameraViewProps {
  videoRef: RefObject<HTMLVideoElement>;
  status: 'disconnected' | 'connecting' | 'connected';
  isAiSpeaking: boolean;
  children?: React.ReactNode;
}

export function CameraView({ videoRef, status, isAiSpeaking, children }: CameraViewProps) {
  const statusColor =
    status === 'connected'
      ? 'bg-green-500'
      : status === 'connecting'
        ? 'bg-yellow-500'
        : 'bg-red-500';

  return (
    <div
      className={`relative w-full h-full overflow-hidden bg-black ${
        isAiSpeaking ? 'animate-glow-border rounded-lg' : ''
      }`}
    >
      <video
        ref={videoRef}
        autoPlay
        playsInline
        muted
        className="absolute inset-0 w-full h-full object-cover"
      />

      {/* Bottom gradient overlay */}
      <div className="absolute inset-x-0 bottom-0 h-32 bg-gradient-to-t from-black/70 to-transparent pointer-events-none" />

      {/* Top gradient overlay */}
      <div className="absolute inset-x-0 top-0 h-16 bg-gradient-to-b from-black/50 to-transparent pointer-events-none" />

      {/* Status indicator */}
      <div className="absolute top-3 left-3 flex items-center gap-2 z-10">
        <div className={`w-2.5 h-2.5 rounded-full ${statusColor} ${status === 'connected' ? 'animate-pulse-recording' : ''}`} />
        <span className="text-xs text-white/70 font-medium uppercase tracking-wider">
          {status}
        </span>
      </div>

      {/* Nexus watermark */}
      <div className="absolute top-3 right-3 z-10">
        <span className="text-xs font-bold text-white/30 tracking-widest uppercase">Nexus</span>
      </div>

      {/* AI speaking indicator */}
      {isAiSpeaking && (
        <div className="absolute top-3 left-1/2 -translate-x-1/2 z-10 flex items-center gap-2 px-3 py-1 rounded-full bg-nexus-primary/20 backdrop-blur-sm border border-nexus-primary/30">
          <div className="w-2 h-2 rounded-full bg-nexus-primary animate-pulse-recording" />
          <span className="text-xs text-nexus-primary font-medium">AI Speaking</span>
        </div>
      )}

      {/* Controls overlay */}
      {children}
    </div>
  );
}
