#!/bin/sh
PROTECTED_BRANCHES="^(main|master|dev|develop)$"

PYTHON_EXEC="python"
# ===========================================

current_branch=$(git symbolic-ref --short HEAD)

echo ""
echo "========================================================"
echo "Pre-push Check [Branch: $current_branch]"

if echo "$current_branch" | grep -E -q "$PROTECTED_BRANCHES"; then
    echo "Protected branch detected. Initiating Safety Checks..."
    echo "Running Pytest..."
    echo "--------------------------------------------------------"

    "$PYTHON_EXEC" -m pytest -v

    EXIT_CODE=$?

    if [ $EXIT_CODE -ne 0 ]; then
        echo "--------------------------------------------------------"
        echo "❌ TESTS FAILED (Exit Code: $EXIT_CODE)"
        echo "   Push blocked! You cannot push broken code to '$current_branch'."
        echo "   Please fix the tests and try again."
        echo "   (Emergency bypass: git push --no-verify)"
        echo "========================================================"
        exit 1
    else
        echo "--------------------------------------------------------"
        echo "All tests passed. Code is safe."
    fi

else
    echo "⚡ Optimization: Skipping tests for non-protected branch."
    echo "   (Tests are enforced only on: $PROTECTED_BRANCHES)"
fi

echo "Proceeding with push..."
echo "========================================================"
exit 0