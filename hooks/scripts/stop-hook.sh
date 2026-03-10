#!/bin/bash
set -euo pipefail

# Project-Finisher Smart Stop Hook
# ----------------------------------
# Phase-aware persistence mechanism for autonomous project completion.
# Reads project state to generate targeted resume prompts instead of
# re-feeding the same prompt every iteration.
#
# Called by Claude Code's Stop hook. Receives JSON on stdin with transcript_path.
# Returns JSON with { decision, reason, systemMessage } to block exit,
# or exits 0 to allow normal exit.

STATE_FILE=".claude/pf-loop.state.json"
PROGRESS_FILE="project_memory/progress.md"
LOG_DIR="${HOME}/.claude/project-finisher-data"
EVOLVE_FLAG="${LOG_DIR}/needs_evolve"

# ------------------------------------------------------------------
# 0. Always set the evolve flag so the next session updates preferences
# ------------------------------------------------------------------
mkdir -p "$LOG_DIR"
date -u +"%Y-%m-%dT%H:%M:%SZ" > "$EVOLVE_FLAG"

# ------------------------------------------------------------------
# 1. Check if continuous loop is active
# ------------------------------------------------------------------
if [[ ! -f "$STATE_FILE" ]]; then
  exit 0  # No loop active, allow normal exit
fi

# ------------------------------------------------------------------
# 2. Read stdin (Claude Code passes JSON with transcript_path)
# ------------------------------------------------------------------
INPUT=$(cat)

# ------------------------------------------------------------------
# 3. Read current phase and milestone from progress.md
#    (using || true to prevent set -e from killing on no match)
# ------------------------------------------------------------------
CURRENT_MILESTONE=""
CURRENT_PHASE=""

if [[ -f "$PROGRESS_FILE" ]]; then
  CURRENT_MILESTONE=$(grep -A5 "## Current Milestone" "$PROGRESS_FILE" | grep "^### " | head -1 | sed 's/^### //' | sed 's/^Milestone: //' || true)
  CURRENT_PHASE=$(grep "^\- \*\*Phase\*\*:" "$PROGRESS_FILE" | head -1 | sed 's/.*: //' || true)
fi

CURRENT_MILESTONE="${CURRENT_MILESTONE:-unknown}"
CURRENT_PHASE="${CURRENT_PHASE:-brainstorm}"

# ------------------------------------------------------------------
# 4. Delegate all JSON processing to a single Python script
#    All values passed via environment to avoid shell injection.
# ------------------------------------------------------------------
export PF_STATE_FILE="$STATE_FILE"
export PF_PROGRESS_FILE="$PROGRESS_FILE"
export PF_CURRENT_PHASE="$CURRENT_PHASE"
export PF_CURRENT_MILESTONE="$CURRENT_MILESTONE"
export PF_INPUT="$INPUT"
export PF_LOG_DIR="$LOG_DIR"

RESULT=$(python3 << 'PYTHON_EOF'
import json, os, sys

state_file = os.environ['PF_STATE_FILE']
current_phase = os.environ['PF_CURRENT_PHASE']
current_milestone = os.environ['PF_CURRENT_MILESTONE']
hook_input = os.environ['PF_INPUT']
log_dir = os.environ['PF_LOG_DIR']

# --- Load state ---
with open(state_file, 'r') as f:
    state = json.load(f)

total_iter = state.get('total_iterations', 0)
max_total = state.get('max_total', 30)

# --- Extract transcript path and check for signals ---
signal = ""
try:
    transcript_path = json.loads(hook_input).get('transcript_path', '')
except (json.JSONDecodeError, TypeError):
    transcript_path = ''

if transcript_path and os.path.isfile(transcript_path):
    # Read transcript (JSONL) and find last assistant message
    entries = []
    with open(transcript_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except (json.JSONDecodeError, ValueError):
                    pass

    last_text = ''
    for entry in reversed(entries):
        if entry.get('role') == 'assistant':
            content = entry.get('content', '')
            if isinstance(content, list):
                texts = [b.get('text', '') for b in content if b.get('type') == 'text']
                content = ' '.join(texts)
            if content.strip():
                last_text = content
                break

    if '<pf-signal>GOAL_COMPLETE</pf-signal>' in last_text:
        signal = 'GOAL_COMPLETE'
    elif '<pf-signal>BLOCKED:' in last_text:
        import re
        m = re.search(r'<pf-signal>BLOCKED:([^<]*)</pf-signal>', last_text)
        if m:
            signal = 'BLOCKED:' + m.group(1)

# --- Handle exit signals ---
if signal == 'GOAL_COMPLETE':
    os.remove(state_file)
    print(json.dumps({"action": "exit"}))
    sys.exit(0)

if signal.startswith('BLOCKED:'):
    reason = signal[len('BLOCKED:'):]
    # Log the block reason
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, 'loop_events.log')
    import datetime
    with open(log_file, 'a') as lf:
        lf.write(f"[{datetime.datetime.utcnow().isoformat()}Z] BLOCKED: {reason}\n")
    os.remove(state_file)
    print(json.dumps({"action": "exit"}))
    sys.exit(0)

# --- Check total iteration limit ---
if total_iter >= max_total:
    os.remove(state_file)
    print(json.dumps({"action": "exit"}))
    sys.exit(0)

# --- Reset phase counter if phase changed ---
last_phase = state.get('last_phase', '')
phase_iterations = state.get('phase_iterations', {})
if last_phase and last_phase != current_phase:
    phase_iterations[current_phase] = 0

# --- Check per-phase iteration budget ---
phase_iter = phase_iterations.get(current_phase, 0)
budgets = state.get('budgets', {})
phase_budget = budgets.get(current_phase, budgets.get('default', 5))

if phase_iter >= phase_budget:
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, 'loop_events.log')
    import datetime
    with open(log_file, 'a') as lf:
        lf.write(f"[{datetime.datetime.utcnow().isoformat()}Z] BUDGET_EXHAUSTED: phase={current_phase}, iterations={phase_iter}/{phase_budget}\n")
    os.remove(state_file)
    print(json.dumps({"action": "exit"}))
    sys.exit(0)

# --- Increment counters and save ---
state['total_iterations'] = total_iter + 1
phase_iterations[current_phase] = phase_iter + 1
state['phase_iterations'] = phase_iterations
state['last_phase'] = current_phase
state['last_milestone'] = current_milestone

with open(state_file, 'w') as f:
    json.dump(state, f, indent=2)

new_total = total_iter + 1
new_phase_iter = phase_iter + 1

# --- Generate phase-appropriate resume prompt ---
prompts = {
    'brainstorm': (
        f'Continue the project-finisher workflow (--auto --continuous). '
        f'You are in the BRAINSTORM phase for milestone: "{current_milestone}". '
        f'Read project_memory/current_context.md for decisions made so far and '
        f'project_memory/progress.md for acceptance criteria. '
        f'Continue brainstorming rounds until convergence, then advance to the Plan phase.'
    ),
    'plan': (
        f'Continue the project-finisher workflow (--auto --continuous). '
        f'You are in the PLAN phase for milestone: "{current_milestone}". '
        f'Brainstorm decisions are recorded in project_memory/current_context.md. '
        f'Create the implementation plan and save it to docs/plans/. Then advance to Execute.'
    ),
    'execute': (
        f'Continue the project-finisher workflow (--auto --continuous). '
        f'You are in the EXECUTE phase for milestone: "{current_milestone}". '
        f'Check project_memory/current_context.md for the step checklist — '
        f'pick up from the first unchecked step. Implement, test, commit. '
        f'When all steps are done, advance to Review.'
    ),
    'review': (
        f'Continue the project-finisher workflow (--auto --continuous). '
        f'You are in the REVIEW phase for milestone: "{current_milestone}". '
        f'Run tests, check acceptance criteria in project_memory/progress.md, '
        f'update lessons.md, and decide whether to advance to the next milestone '
        f'or re-enter Execute.'
    ),
}
resume_prompt = prompts.get(current_phase, (
    f'Continue the project-finisher workflow. '
    f'Read project_memory/progress.md to determine current state.'
))

sys_msg = (
    f'Project-Finisher continuous loop | '
    f'Iteration {new_total}/{max_total} | '
    f'Phase: {current_phase} ({new_phase_iter}/{phase_budget}) | '
    f'Milestone: {current_milestone} | '
    f'To stop: output <pf-signal>GOAL_COMPLETE</pf-signal> when all milestones are done, '
    f'or <pf-signal>BLOCKED:reason</pf-signal> if stuck.'
)

print(json.dumps({
    "action": "block",
    "decision": "block",
    "reason": resume_prompt,
    "systemMessage": sys_msg
}))
PYTHON_EOF
)

# ------------------------------------------------------------------
# 5. Act on the Python result
# ------------------------------------------------------------------
ACTION=$(echo "$RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('action','exit'))" 2>/dev/null || echo "exit")

if [[ "$ACTION" == "exit" ]]; then
  exit 0
fi

# Output the block decision JSON (strip the internal "action" field)
echo "$RESULT" | python3 -c "
import sys, json
r = json.load(sys.stdin)
r.pop('action', None)
json.dump(r, sys.stdout)
"
