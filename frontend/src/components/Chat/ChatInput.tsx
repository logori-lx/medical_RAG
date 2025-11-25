// src/components/Chat/ChatInput.tsx
import React, { useState, useRef, useEffect } from "react";

export interface ChatInputProps {
  onSend: (text: string) => Promise<void> | void;
  placeholder?: string;
}

const ChatInput: React.FC<ChatInputProps> = ({ onSend, placeholder }) => {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  useEffect(() => {
    // autosize
    const ta = textareaRef.current;
    if (!ta) return;
    ta.style.height = "auto";
    ta.style.height = `${ta.scrollHeight}px`;
  }, [value]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
      e.preventDefault();
      doSend();
    }
  };

  const doSend = () => {
    const trimmed = value.trim();
    if (!trimmed) return;
    onSend(trimmed);
    setValue("");
    textareaRef.current?.focus();
  };

  return (
    <div className="p-4 border-t bg-gray-50">
      <div className="max-w-3xl mx-auto flex gap-3 items-end">
        <textarea
          ref={textareaRef}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder || "输入你的问题，按 Ctrl/Cmd+Enter 发送"}
          className="flex-1 min-h-[44px] max-h-48 resize-none p-3 rounded-lg border focus:outline-none focus:ring"
        />
        <div className="flex items-center gap-2">
          <button
            onClick={doSend}
            className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:opacity-95"
          >
            发送
          </button>
        </div>
      </div>
    </div>
  );
};

export default ChatInput;
