// src/services/chat.ts
import axios from "axios";

/**
 * 后端返回的 context 每一项结构
 */
export interface BackendContextItem {
  ask: string;
  answer: string;
  department?: string;
}

/**
 * 后端原始返回结构（你刚刚发给我的那种）
 *
 * {
 *   "answer": "……总结回答……",
 *   "context": [
 *     { "ask": "...", "answer": "...", "department": "..." },
 *     ...
 *   ]
 * }
 */
export interface BackendResponse {
  answer: string;
  context?: BackendContextItem[];
}

/**
 * 给前端用的 askQuestion：
 * 直接把后端的 answer / context 原样返回，
 * ChatPage 里已经用 res.answer / res.context 取字段了。
 */
export async function askQuestion(
  question: string
): Promise<BackendResponse> {
  const resp = await axios.post("/api/user/ask", { question });
  const data = resp.data || {};

  return {
    answer: data.answer ?? "",
    context: Array.isArray(data.context) ? data.context : [],
  };
}
