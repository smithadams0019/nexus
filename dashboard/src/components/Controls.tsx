import { Mic, MicOff, SwitchCamera, Monitor, PhoneOff } from 'lucide-react';

interface ControlsProps {
  isMuted: boolean;
  mediaMode: 'camera' | 'screen';
  onToggleMute: () => void;
  onSwitchCamera: () => void;
  onToggleScreenShare: () => void;
  onDisconnect: () => void;
}

export function Controls({
  isMuted,
  mediaMode,
  onToggleMute,
  onSwitchCamera,
  onToggleScreenShare,
  onDisconnect,
}: ControlsProps) {
  return (
    <div className="absolute bottom-4 left-1/2 -translate-x-1/2 z-20 flex items-center gap-3">
      {/* Mic toggle */}
      <button
        onClick={onToggleMute}
        className={`w-12 h-12 rounded-full flex items-center justify-center backdrop-blur-md transition-colors ${
          isMuted
            ? 'bg-red-500/80 hover:bg-red-500'
            : 'bg-white/10 hover:bg-white/20 border border-white/10'
        }`}
        aria-label={isMuted ? 'Unmute microphone' : 'Mute microphone'}
      >
        {isMuted ? (
          <MicOff className="w-5 h-5 text-white" />
        ) : (
          <Mic className="w-5 h-5 text-white" />
        )}
      </button>

      {/* Camera flip */}
      <button
        onClick={onSwitchCamera}
        disabled={mediaMode === 'screen'}
        className="w-12 h-12 rounded-full flex items-center justify-center bg-white/10 hover:bg-white/20 backdrop-blur-md border border-white/10 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
        aria-label="Switch camera"
      >
        <SwitchCamera className="w-5 h-5 text-white" />
      </button>

      {/* Screen share */}
      <button
        onClick={onToggleScreenShare}
        className={`w-12 h-12 rounded-full flex items-center justify-center backdrop-blur-md transition-colors ${
          mediaMode === 'screen'
            ? 'bg-nexus-primary/80 hover:bg-nexus-primary border border-nexus-primary/50'
            : 'bg-white/10 hover:bg-white/20 border border-white/10'
        }`}
        aria-label={mediaMode === 'screen' ? 'Switch to camera' : 'Share screen'}
      >
        <Monitor className="w-5 h-5 text-white" />
      </button>

      {/* Disconnect */}
      <button
        onClick={onDisconnect}
        className="w-12 h-12 rounded-full flex items-center justify-center bg-red-600/80 hover:bg-red-600 backdrop-blur-md transition-colors"
        aria-label="Disconnect"
      >
        <PhoneOff className="w-5 h-5 text-white" />
      </button>
    </div>
  );
}
