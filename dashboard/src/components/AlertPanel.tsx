import { useEffect } from 'react';
import { X, AlertTriangle, Info, AlertOctagon } from 'lucide-react';

interface Alert {
  id: string;
  severity: 'info' | 'warning' | 'critical';
  message: string;
  timestamp: number;
}

interface AlertPanelProps {
  alerts: Alert[];
  onDismiss: (id: string) => void;
}

const severityConfig: Record<
  Alert['severity'],
  { bg: string; border: string; icon: typeof Info }
> = {
  info: { bg: 'bg-blue-500/10', border: 'border-blue-500/30', icon: Info },
  warning: { bg: 'bg-yellow-500/10', border: 'border-yellow-500/30', icon: AlertTriangle },
  critical: { bg: 'bg-red-500/10', border: 'border-red-500/30', icon: AlertOctagon },
};

function AlertItem({ alert, onDismiss }: { alert: Alert; onDismiss: (id: string) => void }) {
  const config = severityConfig[alert.severity];
  const Icon = config.icon;

  useEffect(() => {
    if (alert.severity === 'info') {
      const timer = setTimeout(() => onDismiss(alert.id), 10000);
      return () => clearTimeout(timer);
    }
  }, [alert.id, alert.severity, onDismiss]);

  return (
    <div
      className={`animate-slide-in-right ${config.bg} border ${config.border} rounded-lg px-3 py-2.5 flex items-start gap-2 ${
        alert.severity === 'critical' ? 'animate-pulse-critical' : ''
      }`}
    >
      <Icon className="w-4 h-4 mt-0.5 shrink-0 text-white/70" />
      <p className="flex-1 text-xs text-white/80 leading-relaxed">{alert.message}</p>
      <button
        onClick={() => onDismiss(alert.id)}
        className="shrink-0 w-5 h-5 flex items-center justify-center rounded-full hover:bg-white/10 transition-colors"
        aria-label="Dismiss alert"
      >
        <X className="w-3 h-3 text-white/50" />
      </button>
    </div>
  );
}

export function AlertPanel({ alerts, onDismiss }: AlertPanelProps) {
  if (alerts.length === 0) return null;

  return (
    <div className="fixed top-14 right-3 z-50 w-72 space-y-2">
      {alerts.map((alert) => (
        <AlertItem key={alert.id} alert={alert} onDismiss={onDismiss} />
      ))}
    </div>
  );
}
