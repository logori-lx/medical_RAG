import os
import sys
import re
import requests
from git import Repo
from zhipuai import ZhipuAI

# ==========================================
# 环境配置 & 路径 Hack
# ==========================================
# [关键] 将当前脚本所在目录(.git/hooks)加入 sys.path，以便能 import 同目录下的 retrieval 和 rerank
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

# 尝试导入同级模块 (这些文件需由安装器一同下载)
try:
    from retrieval import Retrieval
    from rerank import Reranker
except ImportError:
    # 如果没下载全，定义空类防报错
    Retrieval = None
    Reranker = None

# Windows 编码修复
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except: pass

SERVER_BASE_URL = "http://localhost:8000"
CONFIG_URL = f"{SERVER_BASE_URL}/api/v1/config"
TRACK_URL = f"{SERVER_BASE_URL}/api/v1/track"
API_KEY = os.getenv("MEDICAL_RAG")

try:
    repo_obj = Repo(".", search_parent_directories=True)
    REPO_PATH = repo_obj.working_tree_dir
except:
    REPO_PATH = "."

# ==========================================
# 辅助函数
# ==========================================
def get_console_input(prompt_text):
    print(prompt_text, end='', flush=True)
    try:
        if sys.platform == 'win32':
            with open('CON', 'r', encoding='utf-8') as f: return f.readline().strip()
        else:
            with open('/dev/tty', 'r', encoding='utf-8') as f: return f.readline().strip()
    except: return input().strip()

def fetch_dynamic_rules():
    try:
        resp = requests.get(CONFIG_URL, timeout=1.5)
        if resp.status_code == 200: return resp.json()
    except: pass
    return {"template_format": "Standard", "custom_rules": "None"}

def report_to_cloud(msg, risk, summary):
    try:
        user = os.getenv("USERNAME") or "Unknown"
        payload = {
            "developer_id": user,
            "repo_name": os.path.basename(os.path.abspath(REPO_PATH)),
            "commit_msg": msg,
            "risk_level": risk,
            "ai_summary": summary
        }
        requests.post(TRACK_URL, json=payload, timeout=2)
    except: pass

# ==========================================
# 核心逻辑：获取 Diff -> Hybrid Retrieve -> Rerank
# ==========================================
def process_changes_with_rag():
    if not API_KEY or Retrieval is None: 
        return {}, ""

    # 1. 获取 Diff
    try:
        repo = Repo(REPO_PATH)
        try:
            diff_index = repo.head.commit.diff()
        except ValueError:
            EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
            diff_index = repo.tree(EMPTY_TREE).diff(repo.index)
    except: return {}, ""

    changes = {}
    context_str = ""
    
    # 初始化 RAG 组件
    retriever = Retrieval()
    reranker = Reranker()

    for diff in diff_index:
        if diff.change_type == 'D': continue
        fpath = diff.b_path if diff.b_path else diff.a_path
        if not fpath: continue
        
        # 读取 Diff 文本
        try:
            text = repo.git.diff("--cached", fpath)
            if not text.strip(): text = "(New File)"
            _, ext = os.path.splitext(fpath)
            
            # 记录 Change
            changes[fpath] = text

            # --- RAG 流程 ---
            # Step 1: 混合检索 (召回 Top 10)
            candidates = retriever.retrieve_code(query_diff=text, file_ext=ext, top_k=10)
            
            if candidates:
                # Step 2: 重排序 (精选 Top 3)
                final_docs = reranker.rerank(query=text, documents=candidates, top_k=3)
                
                # 拼接上下文
                for doc in final_docs:
                    score = doc.get('score', 0)
                    content = doc.get('answer', '')[:500]
                    context_str += f"\n[Reference from DB (Score: {score:.2f})]:\n{content}\n"

        except Exception: pass

    return changes, context_str

# ==========================================
# 主运行入口
# ==========================================
def run(msg_file_path):
    try:
        with open(msg_file_path, 'r', encoding='utf-8') as f:
            original_msg = f.read().strip()
    except: return
    
    if not original_msg: return

    print(f"🔄 [Git-Guard] Analyzing (Hybrid RAG + Rerank)...")
    
    # 调用 RAG 流程
    changes, context = process_changes_with_rag()
    
    if not changes: return

    # 获取配置
    config = fetch_dynamic_rules()
    fmt = config.get("template_format", "Standard")
    rules = config.get("custom_rules", "")

    # LLM Prompt
    prompt = f"""
    Role: Code Reviewer & Commit Message Generator.
    
    User Draft: "{original_msg}"
    
    Code Changes: 
    {str(list(changes.values()))[:3000]}
    
    Relevant Knowledge Base (Context):
    {context[:1500]}
    
    >>> RULES <<<
    Template: "{fmt}"
    Instructions: "{rules}"
    >>> END RULES <<<
    
    STRICT OUTPUT FORMAT:
    RISK: <High/Medium/Low>
    SUMMARY: <Summary>
    OPTIONS: <Msg1>|||<Msg2>|||<Msg3>
    
    Example:
    OPTIONS: [Backend] fix login|||fix: auth bug|||refactor: login
    """

    try:
        client = ZhipuAI(api_key=API_KEY)
        res = client.chat.completions.create(
            model="glm-4-flash", 
            messages=[{"role": "user", "content": prompt}]
        )
        content = res.choices[0].message.content
        
        # 解析逻辑
        risk = "Medium"
        summary = "Update"
        options = []
        
        for line in content.split('\n'):
            if line.startswith("RISK:"): risk = line.replace("RISK:", "").strip()
            if line.startswith("SUMMARY:"): summary = line.replace("SUMMARY:", "").strip()
            if "OPTIONS:" in line:
                raw = line.split("OPTIONS:")[1].strip()
                options = [p.strip() for p in raw.split('|||') if p.strip()]

        # 清洗选项
        final_options = []
        for opt in options:
            opt = re.sub(r'^[\d\-\.\s]+', '', opt).replace("OPTIONS:", "").strip()
            if len(opt) > 3: final_options.append(opt)
        
        while len(final_options) < 3: final_options.append(f"refactor: {original_msg}")
        options = final_options[:3]

    except Exception as e:
        print(f"AI Failed: {e}")
        return

    # 交互界面
    print("\n" + "="*60)
    print(f"🤖 AI SUGGESTIONS (Risk: {risk})")
    print("="*60)
    print(f"[0] [Keep Original]: {original_msg}")
    print(f"[1] {options[0]}")
    print(f"[2] {options[1]}")
    print(f"[3] {options[2]}")
    print("="*60)

    sel = get_console_input("\n👉 Select (0-3): ")
    
    final_msg = original_msg
    if sel == '1': final_msg = options[0]
    elif sel == '2': final_msg = options[1]
    elif sel == '3': final_msg = options[2]

    if final_msg != original_msg:
        with open(msg_file_path, 'w', encoding='utf-8') as f:
            f.write(final_msg)
        print("✅ Updated.")

    report_to_cloud(final_msg, risk, summary)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        run(sys.argv[1])