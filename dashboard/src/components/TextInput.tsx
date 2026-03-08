import { useState, type KeyboardEvent } from 'react';
import { Send } from 'lucide-react';

interface TextInputProps {
  onSend: (text: string) => void;
  disabled: boolean;
}

export function TextInput({ onSend, disabled }: TextInputProps) {
  const [text, setText] = useState('');

  const handleSend = () => {
    if (text.trim() && !disabled) {
      onSend(text.trim());
      setText('');
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex items-center gap-2 px-3 py-2 bg-nexus-surface/50 border-t border-nexus-border">
      <input
        type="text"
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={disabled ? 'Connect to start...' : 'Type a message or action (e.g. "open Chrome")'}
        disabled={disabled}
        className="flex-1 bg-nexus-dark/50 border border-nexus-border rounded-full px-4 py-2.5 text-sm text-white placeholder-white/30 focus:outline-none focus:border-nexus-primary/50 transition-colors disabled:opacity-40"
      />
      <button
        onClick={handleSend}
        disabled={disabled || !text.trim()}
        className="w-10 h-10 rounded-full bg-nexus-primary flex items-center justify-center shrink-0 transition-opacity disabled:opacity-30 hover:bg-nexus-primary/80"
        aria-label="Send message"
      >
        <Send className="w-4 h-4 text-white" />
      </button>
    </div>
  );
}
