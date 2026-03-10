---
name: finish
description: "Start or continue the project-finisher autonomous completion workflow"
argument-hint: "--goal <path> [--project <path>] [--auto] [--continuous]"
---

# /finish Command

## Parse Arguments

Extract the following from the user's command:

- `--goal <path>`: Path to the goal file. **Required** on first run (when no `project_memory/` directory exists).
- `--project <path>`: Path to the target project directory. Defaults to the current working directory if not provided.
- `--auto`: Enable **auto mode**. When set, the workflow runs with minimal user interaction — all decision points that would normally stop and ask the user are resolved automatically by the orchestrator (see "Auto Mode" below).
- `--continuous`: Enable **continuous loop mode**. Requires `--auto`. When Claude finishes a session, a Stop hook automatically re-invokes the workflow with a phase-appropriate prompt. The loop continues until all milestones are complete, a blocker is hit, or iteration budgets are exhausted. See "Continuous Mode" below.

Resolve all paths to absolute paths before proceeding.

---

## Auto Mode

When `--auto` is passed, the workflow operates with maximum autonomy:

- **Milestone approval**: Initial milestones are accepted as-proposed without waiting for user confirmation.
- **First-run confirmation**: The "Ready to begin?" prompt is skipped — work starts immediately.
- **Brainstorming decisions**: When brainstorming surfaces equally viable approaches, the orchestrator picks the best option based on its own evaluation. If no option is clearly superior, it chooses the **recommended** one (the one `/scientific-brainstorming` endorses, or the simplest approach that satisfies acceptance criteria).
- **All "stop and ask" points**: Instead of stopping, the orchestrator makes the decision autonomously, documents its reasoning in `current_context.md` under "Key Decisions", and continues. The only exception is **external resources needed** (API keys, credentials, hardware) — auto mode still stops for those since it cannot provision them.

Auto mode is propagated to the orchestrate skill so it applies throughout all phases.

**Decision logic for auto mode** (applied at every decision point):
1. If one option is clearly better (lower risk, simpler, better aligned with the goal) → choose it.
2. If the brainstorming output explicitly recommends an approach → follow the recommendation.
3. If options are truly equivalent → choose the simplest one (fewest files, fewest dependencies, most conventional approach).
4. Document the choice and reasoning in `current_context.md` so the user can review it later.

---

## Continuous Mode

When `--continuous` is passed (must be combined with `--auto`), the workflow persists across session boundaries automatically via a Stop hook.

### Setup

On first invocation with `--continuous`, create the loop state file at `.claude/pf-loop.state.json`:

```json
{
  "active": true,
  "started_at": "YYYY-MM-DDTHH:MM:SSZ",
  "total_iterations": 0,
  "max_total": 30,
  "budgets": {
    "brainstorm": 3,
    "plan": 2,
    "execute": 8,
    "review": 3
  },
  "phase_iterations": {},
  "last_phase": "",
  "last_milestone": ""
}
```

Create the `.claude/` directory if it does not exist.

### How It Works

1. The Stop hook (`hooks/scripts/stop-hook.sh`) fires whenever Claude attempts to exit.
2. It reads `.claude/pf-loop.state.json` — if absent, exit is allowed normally.
3. It checks for **exit signals** in Claude's last message:
   - `<pf-signal>GOAL_COMPLETE</pf-signal>` — All milestones satisfied. Loop ends.
   - `<pf-signal>BLOCKED:reason</pf-signal>` — Cannot continue autonomously. Loop ends.
4. It checks iteration budgets (per-phase and total). If exhausted, loop ends.
5. Otherwise, it reads `project_memory/progress.md` for the current phase and milestone, generates a **phase-appropriate resume prompt**, and blocks exit.
6. Claude starts a fresh session with the resume prompt and continues the workflow.

### Phase Iteration Budgets

Each phase has a maximum number of iterations (sessions) it can consume before the loop exits:

| Phase | Default Budget | Rationale |
|-------|---------------|-----------|
| brainstorm | 3 | 2-3 rounds typical; more suggests the milestone needs re-scoping |
| plan | 2 | Planning should converge quickly |
| execute | 8 | Largest phase; complex milestones may need multiple sessions |
| review | 3 | Allows re-entry to execute if criteria aren't met |

The total iteration cap (`max_total`: 30) is a safety net across all milestones.

**Important**: If any phase exhausts its budget, the **entire continuous loop terminates** (not just the phase). This is a safety measure — a phase consuming its full budget suggests the milestone needs re-scoping or user attention. The event is logged to `~/.claude/project-finisher-data/loop_events.log`.

### Phase Iteration Reset

When the stop hook detects that `last_phase` in the state file differs from the current phase in `progress.md`, the phase iteration counter resets to 0 for the new phase. This means advancing from brainstorm to plan resets the counter, giving the plan phase its full budget.

### Cancellation

Use `/cancel-loop` to stop the continuous loop at any time. This removes `.claude/pf-loop.state.json`.

---

## Arguments Not Provided

If `--goal` is missing, check whether `project_memory/progress.md` exists at the project root:

- **If it exists**: Treat this as a continuing run (see "Continuing Run" below).
- **If it does not exist**: Ask the user for the goal file path before proceeding. Do not guess or assume a goal.

---

## First Run (no `project_memory/` directory exists)

Execute these steps in order:

1. **Read the goal file** completely. Parse and understand every requirement, constraint, and success criterion it contains.

2. **Confirm with the user** before making any changes:
   > I'll be working on **[project path]** toward the goal described in **[goal path]**. Ready to begin?

   - **Normal mode**: Wait for explicit user confirmation before continuing.
   - **Auto mode**: Log the message for the record but proceed immediately without waiting.

3. **Create the `project_memory/` directory** at the project root with these initialized files:
   - `progress.md` — populated with the goal summary extracted from the goal file, an empty "Completed Milestones" section, and empty "Current Milestone" and "Upcoming Milestones" sections.
   - `current_context.md` — initialized with the template structure (empty sections ready for the first milestone).
   - `lessons.md` — initialized with the template header only.

   Use the memory skill to set up these files with the correct formats defined in `skills/memory/references/file-formats.md`.

4. **Analyze the project's current state**: Read the project's existing files, structure, and any existing code to understand the starting point.

5. **Propose initial milestones** (3-5) based on:
   - The goal file requirements
   - The current project state
   - The milestone scoping rules from the orchestrate skill (session-completable, 2-5 acceptance criteria, fewer than 15 files, independent value, clear boundary)

6. **Present the milestones to the user** for approval. For each milestone, show:
   - Name
   - Rough scope (one sentence)
   - Acceptance criteria (2-5 items)
   - Priority and dependency information

   - **Normal mode**: Ask the user to approve, modify, or reorder the milestones.
   - **Auto mode**: Display the milestones for the record, then approve them automatically and proceed.

7. **If `--continuous` is active**, create `.claude/pf-loop.state.json` with the default budgets (see "Continuous Mode" above). Create the `.claude/` directory if needed.

8. **Once approved**, write the milestones to `progress.md` (first as current, rest as upcoming) and begin the orchestration loop by invoking the orchestrate skill. Pass the `--auto` flag through to the orchestrate skill if auto mode is active.

---

## Continuing Run (`project_memory/` exists)

Execute these steps in order:

1. **Read `project_memory/progress.md`** to determine:
   - The current milestone name and its phase (brainstorm, plan, execute, or review)
   - How many milestones are completed
   - How many milestones remain (current + upcoming)

2. **Report to the user**:
   > Resuming project. Current milestone: **[title]**, Phase: **[phase]**. [N completed] milestones completed, [M remaining] milestones remaining.

3. **Continue the orchestration loop** from the current phase by invoking the orchestrate skill. Do not restart from the beginning of the current milestone — pick up exactly where the previous session left off.
