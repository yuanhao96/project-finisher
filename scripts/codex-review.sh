#!/usr/bin/env bash
set -euo pipefail

# External milestone reviewer using Codex CLI.
# Scores each rubric dimension 1-10, writes structured JSON output.
#
# Usage: codex-review.sh <project-dir> [--round N]
# Output: <project-dir>/project_memory/review.json
# Exit 0: success, Exit 1: failure (review.json contains error key)

PROJECT_DIR="${1:?Usage: codex-review.sh <project-dir> [--round N]}"
ROUND=1
if [[ "${2:-}" == "--round" ]]; then
  ROUND="${3:?--round requires a number}"
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SCHEMA="$SCRIPT_DIR/codex-review-schema.json"
PROGRESS="$PROJECT_DIR/project_memory/progress.md"
CONTEXT="$PROJECT_DIR/project_memory/current_context.md"
OUTPUT="$PROJECT_DIR/project_memory/review.json"
CODEX_TIMEOUT=180

# Verify required files exist
for f in "$SCHEMA" "$PROGRESS" "$CONTEXT"; do
  if [[ ! -f "$f" ]]; then
    echo "ERROR: Required file not found: $f" >&2
    echo '{"error":"missing_file","detail":"'"$f"'"}' > "$OUTPUT"
    exit 1
  fi
done

# Verify codex is available
if ! command -v codex &>/dev/null; then
  echo "ERROR: codex CLI not found in PATH" >&2
  echo '{"error":"codex_not_found"}' > "$OUTPUT"
  exit 1
fi

# Extract milestone name from Current Milestone section
MILESTONE=$(sed -n \
  '/^## Current Milestone/,/^## /{/^### Milestone:/s/### Milestone: //p}' \
  "$PROGRESS")
if [[ -z "$MILESTONE" ]]; then
  echo "ERROR: No current milestone found in $PROGRESS" >&2
  echo '{"error":"no_current_milestone"}' > "$OUTPUT"
  exit 1
fi

# Extract goal summary (first section content)
GOAL_SUMMARY=$(sed -n \
  '/^## Goal Summary/,/^## /{/^## /d;p}' "$PROGRESS" \
  | head -5)

# Extract acceptance criteria
CRITERIA=$(sed -n \
  '/^## Current Milestone/,/^## Upcoming/{/^[[:space:]]*- \[/p}' \
  "$PROGRESS")

# Extract milestone rubric (between ## Milestone Rubric and next ##)
RUBRIC=$(sed -n \
  '/^## Milestone Rubric/,/^## /{/^## Milestone Rubric/d;/^## /d;p}' \
  "$CONTEXT")
if [[ -z "$RUBRIC" ]]; then
  echo "ERROR: No milestone rubric found in $CONTEXT" >&2
  echo '{"error":"no_rubric"}' > "$OUTPUT"
  exit 1
fi

# Extract latest score card (if any, for delta comparison)
SCORES=$(sed -n '/^## Score Cards/,/\Z/{/^## Score Cards/d;p}' "$CONTEXT")

# Build the prompt
read -r -d '' PROMPT <<PROMPT_EOF || true
You are an independent code reviewer scoring a software milestone.

PROJECT DIRECTORY: $PROJECT_DIR
MILESTONE: $MILESTONE
SCORING ROUND: $ROUND

GOAL SUMMARY:
$GOAL_SUMMARY

ACCEPTANCE CRITERIA:
$CRITERIA

MILESTONE RUBRIC (use these descriptors to calibrate scores):
$RUBRIC

PREVIOUS SCORES (for context, if any):
$SCORES

INSTRUCTIONS:
1. Read the project's source code and tests in $PROJECT_DIR.
2. Run the project's test suite if one exists.
3. Score each dimension in the rubric from 1-10. Use the rubric descriptors:
   - 1-3 means the 'low' descriptor applies
   - 7-10 means the 'high' descriptor applies
   - 4-6 means partial progress between the two
4. Cite specific file paths and line numbers as evidence for each score.
5. Compute the weighted average: sum(weight * score) / sum(weight).
6. List any concerns (issues found, gaps, risks). Use an empty array if none.
PROMPT_EOF

# Run Codex with structured output and timeout
TMPOUT=$(mktemp)
trap 'rm -f "$TMPOUT"' EXIT

if ! timeout "$CODEX_TIMEOUT" codex exec \
  --sandbox read-only \
  --output-schema "$SCHEMA" \
  -o "$TMPOUT" \
  -C "$PROJECT_DIR" \
  "$PROMPT" 2>/dev/null; then
  echo "ERROR: codex exec failed or timed out" >&2
  echo '{"error":"codex_exec_failed"}' > "$OUTPUT"
  exit 1
fi

# Validate output and write review.json
if python3 - "$SCHEMA" "$TMPOUT" "$OUTPUT" <<'PYEOF'
import json
import sys

schema_path, tmpout_path, output_path = sys.argv[1], sys.argv[2], sys.argv[3]

with open(tmpout_path) as f:
    data = json.load(f)

# Basic structure check
required = {"scores", "weighted_average", "concerns"}
if not required.issubset(data.keys()):
    print("Missing required keys", file=sys.stderr)
    sys.exit(1)

if not isinstance(data["scores"], list) or len(data["scores"]) == 0:
    print("Scores array is empty", file=sys.stderr)
    sys.exit(1)

for s in data["scores"]:
    for key in ("dimension", "weight", "score", "evidence"):
        if key not in s:
            print(f"Score entry missing key: {key}", file=sys.stderr)
            sys.exit(1)

# Recompute weighted average for accuracy
total_w = sum(s["weight"] for s in data["scores"])
if total_w > 0:
    computed = sum(s["weight"] * s["score"] for s in data["scores"]) / total_w
    data["weighted_average"] = round(computed, 1)

# Optional: validate against JSON Schema if jsonschema is installed
try:
    from jsonschema import validate
    with open(schema_path) as sf:
        schema = json.load(sf)
    validate(data, schema)
except ImportError:
    pass

with open(output_path, "w") as f:
    json.dump(data, f, indent=2)
PYEOF
then
  echo "Review written to $OUTPUT (round $ROUND)"
  exit 0
else
  echo "ERROR: Output validation failed" >&2
  echo '{"error":"validation_failed"}' > "$OUTPUT"
  exit 1
fi
