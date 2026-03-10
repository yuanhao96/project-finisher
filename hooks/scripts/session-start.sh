#!/bin/bash
set -euo pipefail

LOG_DIR="${HOME}/.claude/project-finisher-data"
EVOLVE_FLAG="${LOG_DIR}/needs_evolve"
PREFS_FILE="${LOG_DIR}/workflow_preferences.md"
PROGRESS_FILE="project_memory/progress.md"

# ------------------------------------------------------------------
# 1. Check if the previous session left an evolve flag
# ------------------------------------------------------------------
if [[ -f "$EVOLVE_FLAG" ]]; then
  PREV_SESSION_END=$(cat "$EVOLVE_FLAG")
  rm -f "$EVOLVE_FLAG"
  echo "IMPORTANT: The previous session (ended ${PREV_SESSION_END}) did not update workflow preferences. Before doing anything else, you MUST run the evolve skill's Observe & Extract procedure: read ~/.claude/project-finisher-data/behavior_log.jsonl and ~/.claude/project-finisher-data/workflow_preferences.md, analyze the previous session's pacing/depth/workflow/tool signals, apply the confidence counter logic, and update workflow_preferences.md. Do this NOW before responding to the user's first message."
fi

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
