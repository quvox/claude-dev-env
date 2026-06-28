#!/bin/bash

INPUT=$(cat)

SESSION_ID=$(echo "$INPUT" | python3 -c 'import sys, json; d=json.load(sys.stdin); print(d.get("session_id", "unknown"))' 2>/dev/null || echo "unknown")
PROMPT=$(echo "$INPUT" | python3 -c 'import sys, json; d=json.load(sys.stdin); print(d.get("prompt", "")[:30])' 2>/dev/null || echo "")

FILE="/tmp/claude_prompt_${SESSION_ID}.txt"
echo "$PROMPT" > "$FILE"
