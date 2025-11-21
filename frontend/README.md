---CN VERSION
# Medical RAG 医疗健康咨询助手（前端 + 简易后端）

本项目是一个轻量级的医疗咨询 Demo，包含：

- 🧩 **Vue + Vite 前端（ChatGPT 风格界面 + 打字机效果）**
- ⚙️ **Python 简易后端（模拟大模型 5 秒生成过程）**
- 📚 支持历史会话、删除记录、复制回答、展开案例、自动滚动等

---

## 🚀 功能特性
### 🔹 前端功能
- ChatGPT 风格输入框（圆角胶囊 + 右侧发送箭头）
- 打字机效果（逐字显示回答）
- 自动滚动到底部
- 避免重复提问（编辑中禁止发送）
- 参考案例展开/折叠
- 用户消息 & AI 回答 UI 美化
- 历史对话列表（支持删除、支持新建会话）
- 回答可复制

### 🔹 后端功能（demo.py）
- 模拟模型生成（固定等待 5 秒 → 返回回答 + 案例）
- 支持跨域
- 接口兼容你的前端格式

---

# 📁 项目目录结构

```
project-root/
│── index.html
│── vite.config.js
│── package.json
│── README.md
│── src/
│   ├── App.vue
│   ├── main.js
│   ├── components/
│   │     ├── ChatPage.vue
│   │     ├── HeaderBar.vue
│   │     └── ...
│   ├── assets/
│── public/
│── demo.py
```

---

# 🛠️ 安装与运行

## **1. 安装依赖**
```bash
npm install
```

## **2. 运行前端**
```bash
npm run dev
```

访问：http://localhost:5173/

---

# ⚙️ **3. 运行 Python 后端（demo.py）**

```bash
python demo.py
```

默认地址：http://localhost:886/api/user/ask

---

# 🔧 前端如何连接后端？

前端中已写好请求逻辑：

```js
const res = await fetch("http://localhost:886/api/user/ask", {...})
```

确保后端启动即可。

---

# 🧪 测试方法

1. 启动前端与后端。
2. 在输入框里输入任何问题。
3. 页面会立即显示「编辑中…」。
4. 5 秒后开始逐字播放回答，并显示参考案例。

---

# 💡 常见问题 FAQ

### 输入框文字遮挡？
CSS 已更新，padding 已优化。

### 生成中能否再次提问？
已禁止，逻辑写在 ChatPage.vue 中。

### 自动滚动？
每一行逐字出现时会自动 scrollIntoView，避免手动滚动。

---EN VERSION

# Medical RAG – Medical Consultation Assistant (Frontend + Simple Backend)

This project is a lightweight medical consultation demo, including:

- 🧩 **Vue + Vite frontend (ChatGPT-style UI + typewriter effect)**
- ⚙️ **Python backend (simulates large-model response with 5‑second delay)**
- 📚 Supports conversation history, deletion, copying answers, collapsible cases, auto‑scrolling, etc.

---

## 🚀 Features

### 🔹 Frontend Features
- ChatGPT-style capsule input bar with send arrow
- Typewriter effect for model responses
- Auto scroll-to-bottom during typing
- Prevent sending new message while generating
- Expandable “reference cases”
- Clean UI for user and AI messages
- Conversation history (create/delete sessions)
- Copy AI answer button

### 🔹 Backend Features (demo.py)
- Simulates model generation (fixed 5‑second delay)
- Returns “response + cases” format compatible with frontend
- CORS enabled
- Easy to replace with real model API

---

# 📁 Project Structure

```
project-root/
│── index.html
│── vite.config.js
│── package.json
│── README.md
│── README_EN.md          ← English version (this file)
│── src/
│   ├── App.vue
│   ├── main.js
│   ├── components/
│   │     ├── ChatPage.vue
│   │     ├── HeaderBar.vue
│   │     └── ...
│   ├── assets/
│── public/
│── demo.py
```

---

# 🛠️ Setup & Run

## 1. Install dependencies
```
npm install
```

## 2. Run the frontend
```
npm run dev
```
Frontend will run on:

➡️ http://localhost:5173/

---

# ⚙️ Run the Python Backend (demo.py)

In another terminal:

```
python demo.py
```

Backend URL:

➡️ http://localhost:886/api/user/ask

---

# 🔧 How frontend communicates with backend

The frontend already uses:

```js
const res = await fetch("http://localhost:886/api/user/ask", {...})
```

No modification needed.

---

# 🧪 How to Test

1. Start frontend and backend.
2. Type any question in the input box.
3. Immediately shows “editing…” status.
4. After 5 seconds, typewriter animation begins.
5. Reference cases become available under the answer.

---

# 💡 FAQ

### Text inside input box looks clipped?
This project uses capsule-style input; padding has been adjusted to fix spacing issues.

### Why can't I send messages during generation?
Disabled on purpose to avoid overlapping typewriter animations.

### Auto scroll not working?
Typewriter engine calls `scrollIntoView()` for each appended line to force scroll.

---

