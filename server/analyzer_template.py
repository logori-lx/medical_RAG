# File: server/analyzer_template.py
import os
import sys
import requests # 用于向云端汇报
import chromadb
from typing import List, Dict
from git import Repo
from zhipuai import ZhipuAI

# --- 配置 ---
# 云端服务器地址 (汇报用)
CLOUD_SERVER_URL = "http://localhost:8000/api/v1/track"

# 自动定位项目根目录
try:
    repo_obj = Repo(".", search_parent_directories=True)
    REPO_PATH = repo_obj.working_tree_dir
except:
    REPO_PATH = "."
repo_path = os.path.abspath(REPO_PATH)
print(f"Processing {repo_path}")

# 数据库路径 (假设在项目根目录的 git_guard/chroma_db)
# 实际项目中，安装脚本应该帮忙设置好这个路径
DB_PATH = os.path.join(REPO_PATH, ".git_guard", "chroma_db")
API_KEY = os.getenv("MEDICAL_RAG") 

# 语言映射
EXT_TO_COLLECTION = {
    ".py": "repo_python", ".java": "repo_java", ".js": "repo_js",
    ".ts": "repo_js", ".html": "repo_html", ".go": "repo_go", ".cpp": "repo_cpp"
}

# --- 辅助类与函数 ---

class ZhipuEmbeddingFunction(chromadb.EmbeddingFunction):
    def __init__(self, api_key):
        self.api_key = api_key
        self.client = ZhipuAI(api_key=api_key)
    def __call__(self, input: List[str]) -> List[List[float]]:
        response = self.client.embeddings.create(model="embedding-3", input=input)
        return [data.embedding for data in response.data]

def get_console_input(prompt_text):
    """Windows/Unix 兼容的强制终端输入"""
    print(prompt_text, end='', flush=True)
    try:
        if sys.platform == 'win32':
            with open('CON', 'r') as f: return f.readline().strip()
        else:
            with open('/dev/tty', 'r') as f: return f.readline().strip()
    except:
        return input().strip()

def get_diff_and_context():
    """获取 Diff 和 RAG 上下文"""
    if not API_KEY: return None, None
    try:
        repo = Repo(REPO_PATH)
        # 兼容 Initial Commit
        try:
            diff_index = repo.head.commit.diff()
        except ValueError:
            EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
            diff_index = repo.tree(EMPTY_TREE).diff(repo.index)
    except:
        return None, None

    changes = {}
    for diff in diff_index:
        if diff.change_type == 'D': continue
        # 核心 Fix: 优先取 b_path 解决 New File 问题
        fpath = diff.b_path if diff.b_path else diff.a_path
        if not fpath: continue
        
        _, ext = os.path.splitext(fpath)
        if ext in EXT_TO_COLLECTION:
            col = EXT_TO_COLLECTION[ext]
            try:
                text = repo.git.diff("--cached", fpath)
                if not text.strip(): text = "(New File/Content Unavailable)"
                if col not in changes: changes[col] = ""
                changes[col] += f"\nFile: {fpath}\n{text}\n"
            except: pass

    # RAG 检索
    context = ""
    if os.path.exists(DB_PATH) and changes:
        try:
            client = chromadb.PersistentClient(path=DB_PATH)
            emb = ZhipuEmbeddingFunction(api_key=API_KEY)
            for col_name, content in changes.items():
                try:
                    col = client.get_collection(name=col_name, embedding_function=emb)
                    res = col.query(query_texts=[content], n_results=2)
                    if res['documents']:
                        for doc in res['documents'][0]:
                            context += f"\nContext ({col_name}):\n{doc[:300]}...\n"
                except: pass
        except Exception as e:
            # 数据库连接失败不应该阻塞流程
            pass
            
    return changes, context

def report_to_cloud(msg, risk, summary):
    """向云端服务器汇报"""
    try:
        user = os.getenv("USERNAME") or os.getenv("USER") or "Unknown Developer"
        payload = {
            "developer_id": user,
            "repo_name": os.path.basename(os.path.abspath(REPO_PATH)),
            "commit_msg": msg,
            "risk_level": risk,
            "ai_summary": summary
        }
        # 设置短超时，避免没网时卡住 Git
        requests.post(CLOUD_SERVER_URL, json=payload, timeout=2)
    except:
        pass # 静默失败，不影响用户使用

# --- 主逻辑：Commit Suggestion & Analysis ---
def run(msg_file_path):
    # 1. 读取用户输入的原始消息
    with open(msg_file_path, 'r', encoding='utf-8') as f:
        original_msg = f.read().strip()
    
    if not original_msg: return

    print(f"🔄 [Git-Guard] Analyzing changes for: '{original_msg}'...")
    changes, context = get_diff_and_context()
    
    if not changes: 
        # 如果没有代码变更（比如只改了 README），直接放行
        return

    # 2. 调用 AI 生成建议
    prompt = f"""
    User Draft: "{original_msg}"
    Code Changes: {list(changes.values())}
    Context: {context[:1000]}
    
    Task: 
    1. Assess Risk (Low/Medium/High).
    2. Generate 3 commit messages (Standard, Detailed, Emoji).
    
    Output Format:
    RISK: <Level>
    SUMMARY: <One sentence summary>
    OPTIONS:
    <Option 1>|||<Option 2>|||<Option 3>
    """
    
    try:
        client = ZhipuAI(api_key=API_KEY)
        res = client.chat.completions.create(
            model="glm-4-flash", messages=[{"role": "user", "content": prompt}]
        )
        content = res.choices[0].message.content
        
        # 解析 AI 返回
        risk_level = "Unknown"
        summary = "No summary"
        options = []
        
        for line in content.split('\n'):
            if line.startswith("RISK:"): risk_level = line.replace("RISK:", "").strip()
            if line.startswith("SUMMARY:"): summary = line.replace("SUMMARY:", "").strip()
        
        if "OPTIONS:" in content:
            parts = content.split("OPTIONS:")[1].strip().split('|||')
            options = [p.strip() for p in parts if p.strip()]
            
        while len(options) < 3: options.append("refactor: update code")

    except Exception as e:
        print(f"⚠️ AI Analysis failed: {e}")
        return

    # 3. 交互式选择
    print("\n" + "="*60)
    print(f"🤖 AI SUGGESTIONS (Risk: {risk_level})")
    print("="*60)
    print(f"0️⃣  [Keep Original]: {original_msg}")
    print(f"1️⃣  {options[0]}")
    print(f"2️⃣  {options[1]}")
    print(f"3️⃣  {options[2]}")
    print("="*60)

    selection = get_console_input("\n👉 Select (0-3) [Enter for 0]: ")

    final_msg = original_msg
    if selection == '1': final_msg = options[0]
    elif selection == '2': final_msg = options[1]
    elif selection == '3': final_msg = options[2]
    
    # 4. 写入文件
    if final_msg != original_msg:
        with open(msg_file_path, 'w', encoding='utf-8') as f:
            f.write(final_msg)
        print(f"✅ Message updated.")

    # 5. ☁️ 上报云端
    print("📡 Reporting to Cloud Dashboard...")
    report_to_cloud(final_msg, risk_level, summary)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        run(sys.argv[1])