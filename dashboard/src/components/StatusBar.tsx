import { Wifi, WifiOff } from 'lucide-react';

interface StatusBarProps {
  status: 'disconnected' | 'connecting' | 'connected';
  sessionId: string;
  isStreaming: boolean;
}

export function StatusBar({ status, sessionId, isStreaming }: StatusBarProps) {
  const statusColor =
    status === 'connected'
      ? 'bg-green-500'
      : status === 'connecting'
        ? 'bg-yellow-500'
        : 'bg-red-500';

  return (
    <div className="h-10 bg-nexus-surface/80 backdrop-blur-md border-b border-nexus-border flex items-center justify-between px-3 shrink-0">
      <div className="flex items-center gap-2">
        {status === 'connected' ? (
          <Wifi className="w-3.5 h-3.5 text-green-400" />
        ) : (
          <WifiOff className="w-3.5 h-3.5 text-white/30" />
        )}
        <div className={`w-2 h-2 rounded-full ${statusColor}`} />
        <span className="text-xs text-white/50 font-medium capitalize">{status}</span>
      </div>

      <div className="flex items-center gap-3">
        {sessionId && (
          <span className="text-[10px] text-white/30 font-mono">#{sessionId}</span>
        )}
        {isStreaming && (
          <span className="text-[10px] text-nexus-primary font-medium uppercase tracking-wider">
            Live
          </span>
        )}
      </div>
    </div>
  );
}
