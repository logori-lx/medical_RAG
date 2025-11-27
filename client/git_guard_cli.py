# File: client/git_guard_cli.py
import os
import requests
import stat

SERVER_URL = "http://localhost:8000"

# --- Hook 1: Commit-Msg ---
HOOK_COMMIT_MSG = """#!/bin/sh
PYTHON_EXEC="python"
GIT_DIR=$(git rev-parse --git-dir)
SCRIPT="$GIT_DIR/hooks/git_guard_analyzer.py"
"$PYTHON_EXEC" "$SCRIPT" "$1"
exit $?
"""

# --- Hook 2: Pre-Push ---
HOOK_PRE_PUSH = """#!/bin/sh
PYTHON_EXEC="python"
GIT_DIR=$(git rev-parse --git-dir)
SCRIPT="$GIT_DIR/hooks/git_guard_indexer.py"
LOG_FILE="$GIT_DIR/../indexer_debug.log"

echo "------------------------------------------------"
echo "🚀 Git-Guard: Triggering Knowledge Base Update..."
"$PYTHON_EXEC" "$SCRIPT" > "$LOG_FILE" 2>&1 &
echo "✅ Background indexing started."
echo "------------------------------------------------"
exit 0
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
    print(f"🔧 Git-Guard Installer v3.1")
    print(f"   Target Server: {SERVER_URL}")
    print("-" * 30)

    if not os.path.exists(".git"):
        print("❌ Error: Not a git repo.")
        return

    hooks_dir = os.path.join(".git", "hooks")
    if not os.path.exists(hooks_dir): os.makedirs(hooks_dir)

    # 下载脚本
    if not download_script("analyzer", os.path.join(hooks_dir, "git_guard_analyzer.py")): return
    if not download_script("indexer", os.path.join(hooks_dir, "git_guard_indexer.py")): return

    # 配置 Hooks
    c_path = os.path.join(hooks_dir, "commit-msg")
    with open(c_path, "w", encoding="utf-8") as f: f.write(HOOK_COMMIT_MSG)
    os.chmod(c_path, os.stat(c_path).st_mode | stat.S_IEXEC)

    p_path = os.path.join(hooks_dir, "pre-push")
    with open(p_path, "w", encoding="utf-8") as f: f.write(HOOK_PRE_PUSH)
    os.chmod(p_path, os.stat(p_path).st_mode | stat.S_IEXEC)

    # 清理旧钩子
    old = os.path.join(hooks_dir, "post-commit")
    if os.path.exists(old): os.remove(old)

    print("-" * 30)
    print("🚀 Installation Complete!")

if __name__ == "__main__":
    install()