import { Lightbulb } from 'lucide-react';

interface Insight {
  id: string;
  title: string;
  content: string;
  category: 'anomaly' | 'insight' | 'suggestion' | 'warning';
  timestamp: number;
}

interface InsightCardsProps {
  insights: Insight[];
}

const categoryColors: Record<Insight['category'], string> = {
  anomaly: 'border-l-red-500',
  insight: 'border-l-blue-500',
  suggestion: 'border-l-green-500',
  warning: 'border-l-yellow-500',
};

function formatTime(ts: number): string {
  const d = new Date(ts);
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

export function InsightCards({ insights }: InsightCardsProps) {
  if (insights.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center text-white/20 py-6">
        <Lightbulb className="w-6 h-6 mb-2 opacity-50" />
        <p className="text-xs">Insights will appear here</p>
      </div>
    );
  }

  return (
    <div className="space-y-2 overflow-y-auto max-h-48">
      {insights.map((insight) => (
        <div
          key={insight.id}
          className={`bg-nexus-surface/50 border-l-2 ${categoryColors[insight.category]} rounded-r-lg px-3 py-2`}
        >
          <div className="flex items-center justify-between mb-1">
            <h4 className="text-xs font-semibold text-white/80">{insight.title}</h4>
            <span className="text-[10px] text-white/30">{formatTime(insight.timestamp)}</span>
          </div>
          <p className="text-xs text-white/50 leading-relaxed">{insight.content}</p>
        </div>
      ))}
    </div>
  );
}
