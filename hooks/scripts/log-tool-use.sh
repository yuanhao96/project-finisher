#!/bin/bash
set -euo pipefail

# Logs tool usage to a JSONL file for behavioral analysis.
# Called by PostToolUse hook. Receives tool info via stdin as JSON.
#
# Stdin JSON fields (from Claude Code hooks):
#   tool_name     - name of the tool that was used
#   session_id    - unique session identifier
#   cwd           - current working directory

INPUT=$(cat)

TOOL_NAME=$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('tool_name','unknown'))" 2>/dev/null || echo "unknown")
SESSION_ID=$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('session_id','unknown'))" 2>/dev/null || echo "unknown")
PROJECT_DIR=$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('cwd','unknown'))" 2>/dev/null || echo "unknown")
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Write to the plugin's data directory (shared across projects)
LOG_DIR="${HOME}/.claude/project-finisher-data"
LOG_FILE="${LOG_DIR}/behavior_log.jsonl"

mkdir -p "$LOG_DIR"

# Append a single JSON line
printf '{"ts":"%s","tool":"%s","project":"%s","session":"%s"}\n' \
  "$TIMESTAMP" "$TOOL_NAME" "$PROJECT_DIR" "$SESSION_ID" \
  >> "$LOG_FILE"
