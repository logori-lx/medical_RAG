#!/bin/sh
PYTHON_EXEC="python"
SCRIPT_PATH="git_hook/analyzer.py"

echo "Running Pre-commit Analysis..."
$PYTHON_EXEC "$SCRIPT_PATH" || exit 1