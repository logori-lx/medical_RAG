// src/services/chat.ts
import axios from "axios";

export interface AskResponse {
  response: string;
  context?: string[];
}

export async function askQuestion(question: string): Promise<AskResponse> {
  const resp = await axios.post("/api/user/ask", { question });
  // 假设后端返回 { response, context }
  return resp.data as AskResponse;
}

/* Advanced: 文件上传示例（占位）
export async function uploadFile(file: File) {
  const fd = new FormData();
  fd.append("file", file);
  const resp = await axios.post("/api/user/upload", fd, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return resp.data;
}
*/
