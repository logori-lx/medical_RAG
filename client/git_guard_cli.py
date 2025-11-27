# File: client/git_guard_cli.py
import os
import requests
import stat

SERVER_URL = "http://47.245.121.54:8000"

# --- Hook 1: Commit-Msg (建议模式) ---
HOOK_COMMIT_MSG = """#!/bin/sh
PYTHON_EXEC="python"
GIT_DIR=$(git rev-parse --git-dir)
SCRIPT="$GIT_DIR/hooks/git_guard_analyzer.py"
"$PYTHON_EXEC" "$SCRIPT" "$1"
exit $?
"""

# --- Hook 2: Pre-Push (后台索引模式) ---
HOOK_PRE_PUSH = """#!/bin/sh
PYTHON_EXEC="python"
GIT_DIR=$(git rev-parse --git-dir)
SCRIPT="$GIT_DIR/hooks/git_guard_indexer.py"
LOG_FILE="$GIT_DIR/../indexer_debug.log"

echo "------------------------------------------------"
echo "🚀 Git-Guard: Triggering Knowledge Base Update..."
"$PYTHON_EXEC" "$SCRIPT" >> "$LOG_FILE" 2>&1 &
echo "✅ Background indexing started."
echo "------------------------------------------------"
exit 0
"""

# --- Hook 3: Pre-Commit (报告模式) ---
HOOK_PRE_COMMIT = """#!/bin/sh
PYTHON_EXEC="python"
GIT_DIR=$(git rev-parse --git-dir)
SCRIPT="$GIT_DIR/hooks/git_guard_analyzer.py"

"$PYTHON_EXEC" "$SCRIPT"

# 退出码决定是否允许提交 (如果在 Python 里 exit(1) 则拦截)
exit $?
"""

def download_script(script_type, save_path):
    try:
        print(f"☁️  Fetching {script_type} logic...")
        url = f"{SERVER_URL}/api/v1/scripts/{script_type}"
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            with open(save_path, "w", encoding="utf-8") as f:
                f.write(resp.json().get("code"))
            print(f"✅ Installed: {save_path}")
            return True
        else:
            print(f"❌ Server Error: {resp.status_code}")
            return False
    except Exception as e:
        print(f"❌ Download failed: {e}")
        return False

def install():
    print(f"🔧 Git-Guard Installer v3.3 (Full Suite)")
    print(f"   Target Server: {SERVER_URL}")
    print("-" * 30)

    if not os.path.exists(".git"):
        print("❌ Error: Not a git repo.")
        return

    hooks_dir = os.path.join(".git", "hooks")
    if not os.path.exists(hooks_dir): os.makedirs(hooks_dir)

    # --- 1. 下载 Python 脚本 ---
    analyzer_path = os.path.join(hooks_dir, "git_guard_analyzer.py")
    dl_1 = download_script("analyzer", analyzer_path)
    
    indexer_path = os.path.join(hooks_dir, "git_guard_indexer.py")
    dl_2 = download_script("indexer", indexer_path)

    if not (dl_1 and dl_2):
        print("\n⚠️  WARNING: Script download failed.")
        print("   Running in offline mode (hooks updated but scripts missing).")

    print("-" * 15 + " Updating Hooks " + "-" * 15)

    # 辅助函数：强力写入 Hook
    def write_hook(filename, content):
        path = os.path.join(hooks_dir, filename)
        try:
            if os.path.exists(path):
                os.chmod(path, stat.S_IWRITE)
                os.remove(path)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            os.chmod(path, stat.S_IREAD | stat.S_IWRITE | stat.S_IEXEC)
            print(f"✅ Hook '{filename}' updated successfully.")
        except Exception as e:
            print(f"❌ Failed to update '{filename}': {e}")

    # --- 2. 配置 Hooks ---
    write_hook("commit-msg", HOOK_COMMIT_MSG)
    write_hook("pre-push", HOOK_PRE_PUSH)
    write_hook("pre-commit", HOOK_PRE_COMMIT)

    # --- 3. 清理旧钩子 ---
    old_hook = os.path.join(hooks_dir, "post-commit")
    if os.path.exists(old_hook):
        try:
            os.remove(old_hook)
            print("🗑️  Cleaned up legacy 'post-commit' hook.")
        except: pass

    print("-" * 30)
    print("🚀 Installation Complete!")
    print("   1. 'pre-commit': Runs Impact Analysis Report.")
    print("   2. 'commit-msg': Suggests & Rewrites Messages.")
    print("   3. 'pre-push':   Updates Vector DB (Background).")

if __name__ == "__main__":
    install()