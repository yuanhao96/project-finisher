---
name: finish
description: "Start or continue the project-finisher autonomous completion workflow"
argument-hint: "--goal <path> [--project <path>]"
---

# /finish Command

## Parse Arguments

Extract the following from the user's command:

- `--goal <path>`: Path to the goal file. **Required** on first run (when no `project_memory/` directory exists).
- `--project <path>`: Path to the target project directory. Defaults to the current working directory if not provided.

Resolve all paths to absolute paths before proceeding.

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

   Wait for explicit user confirmation before continuing.

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

   Ask the user to approve, modify, or reorder the milestones.

7. **Once approved**, write the milestones to `progress.md` (first as current, rest as upcoming) and begin the orchestration loop by invoking the orchestrate skill.

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
