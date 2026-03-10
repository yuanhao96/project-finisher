#!/bin/bash
set -euo pipefail

LOG_DIR="${HOME}/.claude/project-finisher-data"
EVOLVE_FLAG="${LOG_DIR}/needs_evolve"
PENDING_FILE="${LOG_DIR}/pending_session_analysis.json"
PREFS_FILE="${LOG_DIR}/workflow_preferences.md"
PROGRESS_FILE="project_memory/progress.md"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# ------------------------------------------------------------------
# 1. Layer 1: Run deterministic session analyzer
#    This processes behavior_log.jsonl and updates quantitative fields
#    in workflow_preferences.md. Writes pending_session_analysis.json
#    if new sessions were found.
# ------------------------------------------------------------------
python3 "${SCRIPT_DIR}/analyze-sessions.py" 2>/dev/null || true

# Clean up legacy evolve flag (no longer needed)
rm -f "$EVOLVE_FLAG"

# ------------------------------------------------------------------
# 2. Layer 2: If pending analysis exists, ask LLM to do qualitative update
# ------------------------------------------------------------------
if [[ -f "$PENDING_FILE" ]]; then
  # Read the pending analysis summary for the LLM
  SESSION_COUNT=$(python3 -c "import json; d=json.load(open('${PENDING_FILE}')); print(len(d.get('new_sessions',[])))" 2>/dev/null || echo "some")
  echo "IMPORTANT: ${SESSION_COUNT} new session(s) detected since last qualitative update. A deterministic script has already updated quantitative stats (tool counts, session log rows) in workflow_preferences.md. You MUST now read ${PENDING_FILE} and update the QUALITATIVE fields in ${PREFS_FILE}: review the 'pending' rows in the Session Log table and fill in pacing/depth/workflow values. Apply the confidence counter logic from the evolve skill. Then delete ${PENDING_FILE} when done."
fi

# ------------------------------------------------------------------
# 3. Show project-finisher status if active
# ------------------------------------------------------------------
if [[ -f "$PROGRESS_FILE" ]]; then
  CURRENT_MILESTONE=$(grep -A5 "## Current Milestone" "$PROGRESS_FILE" | grep "^### " | head -1 | sed 's/^### //' | sed 's/^Milestone: //' || true)
  CURRENT_PHASE=$(grep "^\- \*\*Phase\*\*:" "$PROGRESS_FILE" | head -1 | sed 's/.*: //' || true)

  if [[ -n "$CURRENT_MILESTONE" && -n "$CURRENT_PHASE" ]]; then
    echo "Project Finisher session detected. Current milestone: ${CURRENT_MILESTONE}. Phase: ${CURRENT_PHASE}. Use /finish to resume or /status for details."
  fi
fi
