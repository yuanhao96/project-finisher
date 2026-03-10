#!/bin/bash
set -euo pipefail

# Cancel the project-finisher continuous loop by removing the state file.

STATE_FILE=".claude/pf-loop.state.json"

if [[ -f "$STATE_FILE" ]]; then
  # Read current state for reporting
  TOTAL=$(python3 -c "import json; print(json.load(open('$STATE_FILE')).get('total_iterations',0))" 2>/dev/null || echo "?")
  rm -f "$STATE_FILE"
  echo "Continuous loop cancelled after ${TOTAL} iterations. State file removed."
else
  echo "No active continuous loop found."
fi
