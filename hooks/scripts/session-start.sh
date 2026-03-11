#!/bin/bash
set -euo pipefail

LOG_DIR="${HOME}/.claude/project-finisher-data"
PROGRESS_FILE="project_memory/progress.md"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# ------------------------------------------------------------------
# 1. Run deterministic session analyzer
#    Processes behavior_log.jsonl and fully updates workflow_preferences.md
#    (both quantitative stats AND qualitative classifications).
#    No LLM layer needed.
# ------------------------------------------------------------------
ANALYZE_OUTPUT=$(python3 "${SCRIPT_DIR}/analyze-sessions.py" 2>/dev/null) || true
if [[ -n "$ANALYZE_OUTPUT" ]]; then
  echo "$ANALYZE_OUTPUT"
fi

# Clean up legacy files
rm -f "${LOG_DIR}/needs_evolve"
rm -f "${LOG_DIR}/pending_session_analysis.json"

# ------------------------------------------------------------------
# 2. Show project-finisher status if active
# ------------------------------------------------------------------
if [[ -f "$PROGRESS_FILE" ]]; then
  CURRENT_MILESTONE=$(grep -A5 "## Current Milestone" "$PROGRESS_FILE" | grep "^### " | head -1 | sed 's/^### //' | sed 's/^Milestone: //' || true)
  CURRENT_PHASE=$(grep "^\- \*\*Phase\*\*:" "$PROGRESS_FILE" | head -1 | sed 's/.*: //' || true)

  if [[ -n "$CURRENT_MILESTONE" && -n "$CURRENT_PHASE" ]]; then
    echo "Project Finisher session detected. Current milestone: ${CURRENT_MILESTONE}. Phase: ${CURRENT_PHASE}. Use /finish to resume or /status for details."
  fi
fi
