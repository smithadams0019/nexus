import { useEffect, useRef } from 'react';
import { Mic } from 'lucide-react';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: number;
}

interface ConversationLogProps {
  messages: Message[];
  isAiSpeaking: boolean;
}

function formatTime(ts: number): string {
  const d = new Date(ts);
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function TypingIndicator() {
  return (
    <div className="flex flex-col items-start">
      <div className="max-w-[85%] px-3.5 py-3 rounded-2xl rounded-bl-md bg-nexus-surface border border-nexus-border flex items-center gap-1.5">
        <div className="w-2 h-2 rounded-full bg-nexus-primary/60 animate-typing-dot" />
        <div className="w-2 h-2 rounded-full bg-nexus-primary/60 animate-typing-dot" />
        <div className="w-2 h-2 rounded-full bg-nexus-primary/60 animate-typing-dot" />
      </div>
    </div>
  );
}

export function ConversationLog({ messages, isAiSpeaking }: ConversationLogProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isAiSpeaking]);

  if (messages.length === 0) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center text-white/30 px-6 py-8">
        <div className="w-12 h-12 rounded-full bg-nexus-primary/10 flex items-center justify-center mb-4">
          <Mic className="w-5 h-5 text-nexus-primary/50" />
        </div>
        <p className="text-sm text-center font-medium text-white/30 mb-1">Nexus is listening</p>
        <p className="text-xs text-center text-white/20 leading-relaxed max-w-[200px]">
          Speak naturally or type a message. Point your camera at something to discuss it.
        </p>
        {isAiSpeaking && (
          <div className="mt-4">
            <TypingIndicator />
          </div>
        )}
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
      {isAiSpeaking && <TypingIndicator />}
      <div ref={bottomRef} />
    </div>
  );
}
