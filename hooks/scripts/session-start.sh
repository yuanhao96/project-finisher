#!/bin/bash
set -euo pipefail

PROGRESS_FILE="project_memory/progress.md"

if [[ ! -f "$PROGRESS_FILE" ]]; then
  exit 0
fi

# Extract current milestone and phase
CURRENT_MILESTONE=$(grep -A1 "## Current Milestone" "$PROGRESS_FILE" | tail -1 | sed 's/^### //')
CURRENT_PHASE=$(grep "^\- \*\*Phase\*\*:" "$PROGRESS_FILE" | head -1 | sed 's/.*: //')

if [[ -n "$CURRENT_MILESTONE" && -n "$CURRENT_PHASE" ]]; then
  echo "Project Finisher session detected. Current milestone: ${CURRENT_MILESTONE}. Phase: ${CURRENT_PHASE}. Use /finish to resume or /status for details."
fi
