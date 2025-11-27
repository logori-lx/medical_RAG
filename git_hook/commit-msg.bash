#!/bin/sh

# Windows 下不需要 (也不能) 使用 exec < /dev/tty
# 我们把交互逻辑完全交给 Python 里的 open('CON') 来处理

PYTHON_EXEC="python"
SCRIPT_PATH="git_hook/analyzer.py"

# $1 是 commit message 的文件路径
"$PYTHON_EXEC" "$SCRIPT_PATH" "$1"

# 退出码由 Python 脚本决定 (sys.exit(0) 或 sys.exit(1))
exit $?