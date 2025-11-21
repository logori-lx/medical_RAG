// src/pages/Chat/index.tsx
import React, { useState } from "react";
import MessageList from "../../components/Chat/MessageList";
import ChatInput from "../../components/Chat/ChatInput";
import { askQuestion } from "../../services/chat";
import { v4 as uuidv4 } from "uuid";
import type { Message } from "../../components/Chat/MessageItem";

const ChatPage: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>(() => [
    {
      id: "sys-welcome",
      role: "system",
      text: "欢迎，你可以向我提问医学、学习或其他领域的问题。",
    },
  ]);

  const send = async (text: string) => {
    // 1) append user message
    const userMsg: Message = { id: uuidv4(), role: "user", text };
    setMessages((m) => [...m, userMsg]);

    // 2) append a temporary assistant loading message
    const loadingMsg: Message = { id: "loading-" + Date.now(), role: "assistant", text: "", loading: true };
    setMessages((m) => [...m, loadingMsg]);

    try {
      // call backend
      const res = await askQuestion(text);

      // replace loading message with real response
      setMessages((m) =>
        m.map((msg) =>
          msg.id === loadingMsg.id
            ? { id: uuidv4(), role: "assistant", text: res.response, context: res.context ?? [] }
            : msg
        )
      );
    } catch (err) {
      // replace loading with error message
      setMessages((m) =>
        m.map((msg) =>
          msg.id === loadingMsg.id
            ? { id: uuidv4(), role: "assistant", text: "请求失败，请稍后重试（网络或服务器错误）" }
            : msg
        )
      );
      console.error("askQuestion error", err);
    }
  };

  return (
    <div className="h-screen flex flex-col bg-[#f7f8fa]">
      <header className="bg-white border-b py-3">
        <div className="max-w-3xl mx-auto px-4">
          <h1 className="text-lg font-semibold">DeepSeek 风格对话</h1>
          <p className="text-xs text-gray-500">回答以 append 方式展示；思考（context）展示在每条回答下方。</p>
        </div>
      </header>

      <MessageList messages={messages} />

      <ChatInput onSend={send} placeholder="例：两年前确诊乙肝大三阳，现在复查需要检查哪些项目？" />
    </div>
  );
};

export default ChatPage;
