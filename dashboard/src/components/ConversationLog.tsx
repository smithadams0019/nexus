import { useEffect, useRef } from 'react';
import { MessageSquare } from 'lucide-react';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: number;
}

interface ConversationLogProps {
  messages: Message[];
}

function formatTime(ts: number): string {
  const d = new Date(ts);
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

export function ConversationLog({ messages }: ConversationLogProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  if (messages.length === 0) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center text-white/30 px-4 py-8">
        <MessageSquare className="w-8 h-8 mb-3 opacity-50" />
        <p className="text-sm text-center">Start talking — Nexus is listening...</p>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto px-3 py-3 space-y-3">
      {messages.map((msg) => (
        <div
          key={msg.id}
          className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}
        >
          <div
            className={`max-w-[85%] px-3.5 py-2.5 rounded-2xl text-sm leading-relaxed ${
              msg.role === 'user'
                ? 'bg-nexus-primary text-white rounded-br-md'
                : 'bg-nexus-surface text-white/90 border border-nexus-border rounded-bl-md'
            }`}
          >
            {msg.content}
          </div>
          <span className="text-[10px] text-white/30 mt-1 px-1">
            {formatTime(msg.timestamp)}
          </span>
        </div>
      ))}
      <div ref={bottomRef} />
    </div>
  );
}
