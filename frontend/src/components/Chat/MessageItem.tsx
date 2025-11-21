// src/components/Chat/MessageItem.tsx
import React from "react";

export type Role = "user" | "assistant" | "system";

export interface Message {
  id: string;
  role: Role;
  text: string;
  context?: string[]; // only assistant messages will usually have this
  loading?: boolean;
}

const MessageItem: React.FC<{ msg: Message }> = ({ msg }) => {
  const isUser = msg.role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-3`}>
      <div
        className={
          "max-w-[78%] break-words p-3 rounded-2xl shadow-sm " +
          (isUser
            ? "bg-blue-600 text-white rounded-br-none"
            : "bg-gray-50 text-gray-900 rounded-bl-none border")
        }
      >
        {msg.loading ? (
          <div className="flex items-center gap-2">
            <LoadingDots />
            <span className="text-sm opacity-80">生成中...</span>
          </div>
        ) : (
          <div style={{ whiteSpace: "pre-wrap", fontSize: 15 }}>{msg.text}</div>
        )}

        {/* context 小字显示（仅 assistant） */}
        {msg.context && msg.context.length > 0 && (
          <div className="mt-2 text-gray-500 text-xs leading-snug">
            <small>
              思考（context）：{" "}
              {msg.context.map((c, i) => (
                <span key={i} className="inline-block mr-2">
                  {i + 1}. {c}
                </span>
              ))}
            </small>
          </div>
        )}
      </div>
    </div>
  );
};

function LoadingDots() {
  return (
    <div className="flex gap-1 items-center">
      <span className="w-2 h-2 rounded-full animate-pulse bg-gray-400"></span>
      <span className="w-2 h-2 rounded-full animate-pulse bg-gray-500"></span>
      <span className="w-2 h-2 rounded-full animate-pulse bg-gray-400"></span>
    </div>
  );
}

export default MessageItem;
