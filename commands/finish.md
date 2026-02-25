---
name: finish
description: "Start or continue the project-finisher autonomous completion workflow"
argument-hint: "--goal <path> [--project <path>] [--auto]"
---

# /finish Command

## Parse Arguments

Extract the following from the user's command:

- `--goal <path>`: Path to the goal file. **Required** on first run (when no `project_memory/` directory exists).
- `--project <path>`: Path to the target project directory. Defaults to the current working directory if not provided.
- `--auto`: Enable **auto mode**. When set, the workflow runs with minimal user interaction — all decision points that would normally stop and ask the user are resolved automatically by the orchestrator (see "Auto Mode" below).

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

7. **Once approved**, write the milestones to `progress.md` (first as current, rest as upcoming) and begin the orchestration loop by invoking the orchestrate skill. Pass the `--auto` flag through to the orchestrate skill if auto mode is active.

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
