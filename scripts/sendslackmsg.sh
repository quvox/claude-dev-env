#!/bin/bash
# Claude Code hook: send a Slack notification.
# Reads SLACK_BOT_TOKEN (and optionally SLACK_CHANNEL) from the environment.

CHANNEL="${SLACK_CHANNEL:-U5SJG0XEK}"
TOKEN="${SLACK_BOT_TOKEN:-}"

if [ -z "$TOKEN" ]; then
  exit 0
fi

MSG="${1:-}"
INPUT="$(cat)"

SESSION_ID="$(printf '%s' "$INPUT" | jq -r '.session_id // "unknown"' 2>/dev/null || echo unknown)"

FILE="/tmp/claude_prompt_${SESSION_ID}.txt"
PROMPT="$(cat "$FILE" 2>/dev/null || true)"
if [ -z "$PROMPT" ]; then
  PROMPT="(no prompt)"
fi

PAYLOAD="$(jq -n \
  --arg channel "$CHANNEL" \
  --arg text "${MSG} 「${PROMPT}...」" \
  '{channel: $channel, text: $text}')"

curl -sS -X POST \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json; charset=utf-8" \
  --data "$PAYLOAD" \
  https://slack.com/api/chat.postMessage >/dev/null 2>&1 || true
