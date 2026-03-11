#!/bin/bash
set -euo pipefail

# Logs tool usage to a JSONL file for behavioral analysis.
# Called by PostToolUse hook. Receives tool info via stdin as JSON.
#
# Stdin JSON fields (from Claude Code hooks):
#   tool_name     - name of the tool that was used
#   tool_input    - parameters passed to the tool
#   tool_response - result returned by the tool
#   session_id    - unique session identifier
#   cwd           - current working directory

INPUT=$(cat)

# Extract base fields and optional enrichment fields in a single python call
# to minimize subprocess overhead (hook has 5s timeout)
read -r TOOL_NAME SESSION_ID PROJECT_DIR EDIT_SIZE BASH_OK < <(
  echo "$INPUT" | python3 -c "
import sys, json
d = json.load(sys.stdin)
tool = d.get('tool_name', 'unknown')
sid = d.get('session_id', 'unknown')
cwd = d.get('cwd', 'unknown')
inp = d.get('tool_input', {}) or {}
resp = d.get('tool_response', {}) or {}

# Edit size: net chars changed for Edit, total chars for Write
edit_size = ''
if tool == 'Edit':
    old = inp.get('old_string', '')
    new = inp.get('new_string', '')
    edit_size = str(len(new) - len(old))
elif tool == 'Write':
    content = inp.get('content', '')
    edit_size = str(len(content))

# Bash success: check tool_response for success field
bash_ok = ''
if tool == 'Bash':
    if isinstance(resp, dict):
        bash_ok = '1' if resp.get('success', True) else '0'
    elif isinstance(resp, str):
        bash_ok = '0' if 'error' in resp.lower() or 'exit code' in resp.lower() else '1'

print(tool, sid, cwd, edit_size, bash_ok)
" 2>/dev/null || echo "unknown unknown unknown '' ''"
)

TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Write to the plugin's data directory (shared across projects)
LOG_DIR="${HOME}/.claude/project-finisher-data"
LOG_FILE="${LOG_DIR}/behavior_log.jsonl"

mkdir -p "$LOG_DIR"

# Build JSON with optional fields
EXTRA=""
if [ -n "$EDIT_SIZE" ]; then
  EXTRA="${EXTRA},\"edit_size\":${EDIT_SIZE}"
fi
if [ -n "$BASH_OK" ]; then
  if [ "$BASH_OK" = "1" ]; then
    EXTRA="${EXTRA},\"bash_ok\":true"
  else
    EXTRA="${EXTRA},\"bash_ok\":false"
  fi
fi

printf '{"ts":"%s","tool":"%s","project":"%s","session":"%s"%s}\n' \
  "$TIMESTAMP" "$TOOL_NAME" "$PROJECT_DIR" "$SESSION_ID" "$EXTRA" \
  >> "$LOG_FILE"

# Prune to last 100 entries to prevent unbounded growth
MAX_LINES=100
LINE_COUNT=$(wc -l < "$LOG_FILE" 2>/dev/null || echo 0)
if [ "$LINE_COUNT" -gt "$MAX_LINES" ]; then
  tail -n "$MAX_LINES" "$LOG_FILE" > "$LOG_FILE.tmp" && mv "$LOG_FILE.tmp" "$LOG_FILE"
fi
