# File: server/analyzer_template.py
import os
import sys
import re
import requests 
import chromadb
from typing import List
from git import Repo
from zhipuai import ZhipuAI

# ==========================================
# [FIX] Windows GBK 编码修复
# 强制 Python 的标准输出使用 UTF-8，防止 Emoji 报错
# ==========================================
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass # Python版本过低或环境不支持时忽略

# ==========================================
# 配置常量
# ==========================================
SERVER_BASE_URL = "http://localhost:8000"
CONFIG_URL = f"{SERVER_BASE_URL}/api/v1/config"
TRACK_URL = f"{SERVER_BASE_URL}/api/v1/track"

# 自动定位 Git 根目录
try:
    repo_obj = Repo(".", search_parent_directories=True)
    REPO_PATH = repo_obj.working_tree_dir
except:
    REPO_PATH = "."

# 确保 .git_guard 文件夹存在
GUARD_DIR = os.path.join(REPO_PATH, ".git_guard")
if not os.path.exists(GUARD_DIR):
    try:
        os.makedirs(GUARD_DIR)
    except OSError:
        pass

DB_PATH = os.path.join(GUARD_DIR, "chroma_db")
API_KEY = os.getenv("MEDICAL_RAG") 

# 文件后缀与向量库集合的映射
EXT_TO_COLLECTION = {
    ".py": "repo_python", 
    ".java": "repo_java", 
    ".js": "repo_js",
    ".ts": "repo_js", 
    ".html": "repo_html", 
    ".go": "repo_go", 
    ".cpp": "repo_cpp",
    ".c": "repo_cpp"
}

# ==========================================
# 辅助类与函数
# ==========================================

class ZhipuEmbeddingFunction(chromadb.EmbeddingFunction):
    """智谱 AI Embedding 适配器"""
    def __init__(self, api_key):
        self.api_key = api_key
        self.client = ZhipuAI(api_key=api_key)

    def __call__(self, input: List[str]) -> List[List[float]]:
        response = self.client.embeddings.create(model="embedding-3", input=input)
        return [data.embedding for data in response.data]

def get_console_input(prompt_text):
    """跨平台强制读取终端输入 (绕过 Git Hook stdin)"""
    print(prompt_text, end='', flush=True)
    try:
        if sys.platform == 'win32':
            with open('CON', 'r', encoding='utf-8') as f:
                return f.readline().strip()
        else:
            with open('/dev/tty', 'r', encoding='utf-8') as f:
                return f.readline().strip()
    except Exception:
        # 回退方案
        return input().strip()

def get_diff_and_context():
    """获取暂存区代码变更 + RAG 上下文检索"""
    if not API_KEY: 
        return None, None
    
    # 1. 获取 Git Diff
    try:
        repo = Repo(REPO_PATH)
        try:
            # 正常 diff: HEAD vs Index
            diff_index = repo.head.commit.diff()
        except ValueError:
            # 初始提交: Empty Tree vs Index
            EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
            diff_index = repo.tree(EMPTY_TREE).diff(repo.index)
    except Exception:
        return None, None

    changes = {}
    for diff in diff_index:
        # 跳过删除的文件
        if diff.change_type == 'D': 
            continue
        
        # 优先取 b_path (新路径)
        fpath = diff.b_path if diff.b_path else diff.a_path
        if not fpath: 
            continue
        
        _, ext = os.path.splitext(fpath)
        if ext in EXT_TO_COLLECTION:
            col = EXT_TO_COLLECTION[ext]
            try:
                # 获取暂存区的内容差异
                text = repo.git.diff("--cached", fpath)
                if not text.strip(): 
                    text = "(New File or Content Unavailable)"
                
                if col not in changes: 
                    changes[col] = ""
                changes[col] += f"\nFile: {fpath}\n{text}\n"
            except Exception:
                pass

    # 2. RAG 上下文检索
    context = ""
    if os.path.exists(DB_PATH) and changes:
        try:
            client = chromadb.PersistentClient(path=DB_PATH)
            emb = ZhipuEmbeddingFunction(api_key=API_KEY)
            
            for col_name, content in changes.items():
                try:
                    col = client.get_collection(name=col_name, embedding_function=emb)
                    # 检索最相关的 2 段代码
                    res = col.query(query_texts=[content], n_results=2)
                    if res['documents']:
                        for doc in res['documents'][0]:
                            # 截取前 300 字符防止上下文过长
                            context += f"\nContext ({col_name}):\n{doc[:300]}...\n"
                except Exception:
                    # 集合可能不存在，跳过
                    pass
        except Exception:
            # 数据库连接失败忽略
            pass
            
    return changes, context

def report_to_cloud(msg, risk, summary):
    """向云端 Dashboard 汇报提交活动"""
    try:
        user = os.getenv("USERNAME") or os.getenv("USER") or "Unknown Developer"
        payload = {
            "developer_id": user,
            "repo_name": os.path.basename(os.path.abspath(REPO_PATH)),
            "commit_msg": msg,
            "risk_level": risk,
            "ai_summary": summary
        }
        # 设置短超时避免阻塞
        requests.post(TRACK_URL, json=payload, timeout=2)
    except Exception:
        pass

def fetch_dynamic_rules():
    """从服务器拉取最新的提交规范"""
    try:
        resp = requests.get(CONFIG_URL, timeout=1.5)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    
    # 默认兜底规则
    return {
        "template_format": "Conventional Commits (<type>: <subject>)",
        "custom_rules": "No specific rules. Keep it concise."
    }

# ==========================================
# 主运行逻辑
# ==========================================
def run(msg_file_path):
    # 1. 读取用户原始输入
    try:
        with open(msg_file_path, 'r', encoding='utf-8') as f:
            original_msg = f.read().strip()
    except FileNotFoundError:
        return
    
    if not original_msg: 
        return

    print(f"[Git-Guard] Analyzing changes...")
    
    # 2. 获取 Diff 和 Context
    changes, context = get_diff_and_context()
    
    # 如果没有实质代码变更，直接放行
    if not changes: 
        return

    # 3. 获取云端配置规则
    config = fetch_dynamic_rules()
    fmt = config.get("template_format", "Standard")
    rules = config.get("custom_rules", "")

    # 4. 构建 Prompt (包含具体示例，防止 AI 输出占位符)
    prompt = f"""
    You are a professional code reviewer assistant.
    
    User Draft: "{original_msg}"
    
    Code Changes (Diff snippets): 
    {str(list(changes.values()))[:3000]} 
    
    Context (Related Code): 
    {str(context)[:500]}
    
    Goal: Generate 3 commit messages.
    
    >>> ORGANIZATION RULES <<<
    Target Format: "{fmt}"
    Custom Instructions: "{rules}"
    >>> END RULES <<<
    
    STRICT OUTPUT FORMAT:
    RISK: <High/Medium/Low>
    SUMMARY: <1 sentence summary>
    OPTIONS: <Option1>|||<Option2>|||<Option3>
    
    EXAMPLE OUTPUT (Do NOT copy content, only format):
    RISK: Low
    SUMMARY: Updated user login validation logic.
    OPTIONS: {fmt.replace('<message>', 'update login validation')}|||fix: login error|||✨ feat: enhance auth
    
    IMPORTANT CONSTRAINTS:
    1. Do NOT output "<Msg1>" or placeholders. Generate ACTUAL content based on the code changes.
    2. Use '|||' as the ONLY separator for options.
    3. Do NOT include newlines or numbered lists inside OPTIONS line.
    """
    
    try:
        client = ZhipuAI(api_key=API_KEY)
        res = client.chat.completions.create(
            model="glm-4-flash", 
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        content = res.choices[0].message.content
        
        # 5. 解析 AI 返回结果
        risk_level = "Medium"
        summary = "Code update"
        options = []
        
        for line in content.split('\n'):
            line = line.strip()
            if line.startswith("RISK:"): 
                risk_level = line.replace("RISK:", "").strip()
            if line.startswith("SUMMARY:"): 
                summary = line.replace("SUMMARY:", "").strip()
            if "OPTIONS:" in line:
                raw = line.split("OPTIONS:")[1].strip()
                if "|||" in raw: 
                    options = [p.strip() for p in raw.split('|||') if p.strip()]

        # 6. 数据清洗 (防止 AI 输出 Prompt 里的垃圾信息)
        final_options = []
        for opt in options:
            # 去掉编号 (如 "1. ")
            opt = re.sub(r'^[\d\-\.\s]+', '', opt)
            # 去掉意外混入的 Tag
            opt = opt.replace("OPTIONS:", "").strip()
            
            # 过滤明显错误的占位符
            if "<Msg" in opt or "Option" in opt or "Constraint" in opt: 
                continue
                
            if len(opt) > 3: 
                final_options.append(opt)
        
        # 补齐兜底选项
        while len(final_options) < 3: 
            final_options.append(f"refactor: {original_msg}")
            
        options = final_options[:3]

    except Exception as e:
        print(f"⚠️ AI Analysis failed: {e}")
        # 出错时不阻断，直接返回
        return

    # 7. 用户交互界面
    print("\n" + "="*60)
    print(f"🤖 AI SUGGESTIONS (Risk: {risk_level})")
    print("="*60)
    print(f"[0] [Keep Original]: {original_msg}")
    print(f"[1] {options[0]}")
    print(f"[2] {options[1]}")
    print(f"[3] {options[2]}")
    print("="*60)

    # 8. 获取选择
    selection = get_console_input("\n👉 Select (0-3) [Enter for 0]: ")

    final_msg = original_msg
    if selection == '1': final_msg = options[0]
    elif selection == '2': final_msg = options[1]
    elif selection == '3': final_msg = options[2]
    
    # 9. 覆写 Commit Message
    if final_msg != original_msg:
        try:
            with open(msg_file_path, 'w', encoding='utf-8') as f:
                f.write(final_msg)
            print(f"✅ Message updated.")
        except Exception as e:
            print(f"❌ Failed to update message: {e}")

    # 10. 上报
    report_to_cloud(final_msg, risk_level, summary)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        run(sys.argv[1])