# Phase Prompt Templates

These are the internal prompt templates the orchestrator uses when entering each phase of the iteration loop. Each template specifies what context to load and what questions to work through.

---

## Entering Phase 1: Brainstorm

### Context to Load
- Goal file (the user-provided project goal)
- `project_memory/progress.md` (completed milestones, current milestone, upcoming queue)
- `project_memory/lessons.md` (all lessons from prior milestones)

### Git Setup (before brainstorming)

```
GIT SETUP:
1. Determine milestone number: count completed milestones in progress.md + 1.
2. Check if pf/milestone-{N} branch already exists (session resume):
   - If yes: git checkout pf/milestone-{N} (resume work on existing branch)
   - If no: git checkout -b pf/milestone-{N} <default-branch> (create new branch)
3. If default branch has new commits since last milestone:
   git merge <default-branch>
   If conflicts → BLOCKED signal and stop.
```

### Multi-Round Brainstorming Process

Each round invokes `/scientific-brainstorming`. The pushback from each round becomes the input for the next.

**Round 1 — Feasibility and approach**:

```
/scientific-brainstorming

I'm working on milestone: "{milestone_name}" for the project goal: {goal_summary}.

Completed so far: {list_of_completed_milestones}
Milestone objective: {milestone_objective}
Lessons from prior work: {applicable_lessons}

Questions to brainstorm:
1. Is this milestone feasible as scoped?
2. What are 2-3 possible approaches and their trade-offs?
3. What is the simplest approach that satisfies the acceptance criteria?
4. Are there any lessons from prior milestones that should influence the approach?
5. What concerns or risks do you see?
```

Collect output: recommended approach, concerns raised, open questions.

**Round 2 — Address Round 1 pushback**:

```
/scientific-brainstorming

Continuing brainstorm for milestone: "{milestone_name}".

In the previous round, the following concerns and questions were raised:
{list_of_concerns_and_questions_from_round_1}

The recommended approach was: {approach_from_round_1}

Let's address each concern:
1. For each risk: how do we mitigate it? Is it a blocker or just a watch-item?
2. For each open question: can we answer it now, or does it need to be resolved during planning?
3. Does the recommended approach still hold, or should we pivot?
4. Does the scope still fit the scoping rules (single session, 2-5 criteria, <15 files)?
```

Collect output: resolved concerns, remaining risks, refined approach.

**Round 3+ — Continue until convergence** (if new significant concerns emerged):

```
/scientific-brainstorming

Continuing brainstorm for milestone: "{milestone_name}", round {N}.

Previous round raised these new concerns: {new_concerns_from_previous_round}
Current approach: {refined_approach}

Let's resolve these remaining issues and confirm the approach is solid.
```

**Convergence**: Stop when a round produces no new significant risks or questions.

**After convergence, record in current_context.md**:
- Chosen approach and why (with round number where decided).
- Resolved concerns and how they were resolved.
- Remaining risks to watch for during Plan/Execute.
- Any scope adjustments made.

**Commit brainstorm decisions**:
```
git add project_memory/
git commit -m "pf: brainstorm decisions for milestone {N}"
```

**Rules**:
- Always run at least 2 rounds — never skip the pushback-resolution cycle.
- Do NOT write code or create files.
- If still ambiguous after 3+ rounds, STOP and ask the user (normal mode) or auto-decide (auto mode).
- **Auto mode**: When brainstorming presents options or asks for a choice, auto-select the recommended option. If no recommendation, pick the simplest approach. Log all auto-decisions as `[AUTO]` in `current_context.md`.

---

### Exploratory Branching (after convergence, auto mode only)

If two approaches remain with similar trade-offs and auto mode is active:

```
FORK DECISION:
Two approaches with similar trade-offs identified. Activating exploratory branching.

Approach A: "{approach_a_slug}" — {description}
Approach B: "{approach_b_slug}" — {description}

PROCEDURE:
1. Log [AUTO-EXPLORE] decision in current_context.md
2. Set Exploration Mode to active in current_context.md
3. Create sub-branches:
   git checkout pf/milestone-{N}
   git checkout -b pf/milestone-{N}/a
   git checkout pf/milestone-{N}
   git checkout -b pf/milestone-{N}/b
   git checkout pf/milestone-{N}
4. Commit current_context.md update:
   git add project_memory/
   git commit -m "pf: activate exploratory branching for milestone {N}"
5. Advance to Phase 2 in exploratory mode.
```

---

## Entering Phase 2: Plan

### Context to Load
- Goal file (the user-provided project goal)
- `project_memory/progress.md` (milestone definitions and status)
- `project_memory/current_context.md` (brainstorm decisions, key decisions, open questions)

### Prompt Template (Normal Mode)

```
I am entering the PLAN phase for milestone: "{milestone_name}".

CONTEXT LOADED:
- Goal: {goal_summary}
- Milestone objective: {milestone_objective}
- Brainstorm decisions: {key_decisions_from_current_context}
- Open questions from brainstorm: {open_questions}

PLAN STRUCTURE:
1. FILES — List every file to create or modify:
   - File path: description of change

2. TASKS — Ordered implementation steps:
   - Each task should be a single, verifiable unit of work.
   - Include the expected outcome for each task.
   - Note which files each task touches.

3. TESTS — What to test and how:
   - Unit tests: what functions/modules to test.
   - Integration tests: what workflows to verify.
   - Manual checks: what to inspect visually or via CLI.

4. DEPENDENCY ORDER — Which tasks must complete before others:
   - Task N must complete before Task M because...

5. ROLLBACK NOTES — For risky steps:
   - If step X fails, revert by...

VALIDATION CHECKLIST:
- [ ] Every step is actionable without asking the user.
- [ ] No single task touches more than 5 files.
- [ ] The plan covers all acceptance criteria for this milestone.
- [ ] Test coverage is specified for each acceptance criterion.
- [ ] The plan can be executed by reading only current_context.md.

OUTPUT:
- Save full plan to docs/plans/YYYY-MM-DD-{milestone_slug}.md
- Update current_context.md with the step checklist.
- Set phase to "plan" in current_context.md.
- Commit plan and memory updates:
  git add docs/plans/ project_memory/
  git commit -m "pf: plan for milestone {N}"

RULES:
- The plan must be self-contained and executable without clarification.
- Normal mode: If any step requires user input, STOP and ask before finalizing.
- Auto mode: If a step would normally require user input, make the most reasonable assumption, document it as [AUTO] in current_context.md, and proceed.
```

### Prompt Template (Exploratory Mode)

When `exploration_mode: true` in `current_context.md`:

```
I am entering the PLAN phase for milestone: "{milestone_name}" in EXPLORATORY MODE.

Two approaches were identified during brainstorming:
- Approach A ("{approach_a_slug}"): {description}
- Approach B ("{approach_b_slug}"): {description}

ACCEPTANCE CRITERIA (same for both):
{acceptance_criteria_list}

TASK: Create TWO separate, self-contained plans.

For EACH approach, produce a plan with the same structure as a normal plan:
1. FILES, 2. TASKS, 3. TESTS, 4. DEPENDENCY ORDER, 5. ROLLBACK NOTES

Each plan must be fully self-contained — a subagent reading ONLY that plan file
plus the acceptance criteria can execute it without any other context.

OUTPUT — create and commit plans ONE BRANCH AT A TIME to avoid cross-contamination:

Plan A:
  git checkout pf/milestone-{N}/a
  Create docs/plans/YYYY-MM-DD-{milestone_slug}-approach-a.md
  git add docs/plans/
  git commit -m "pf: plan for milestone {N} — approach A ({approach_a_slug})"
  git checkout pf/milestone-{N}

Plan B:
  git checkout pf/milestone-{N}/b
  Create docs/plans/YYYY-MM-DD-{milestone_slug}-approach-b.md
  git add docs/plans/
  git commit -m "pf: plan for milestone {N} — approach B ({approach_b_slug})"
  git checkout pf/milestone-{N}

IMPORTANT: Create each plan file ONLY while on its target branch.
Do NOT create both files then commit — git add docs/plans/ would stage both.

- Update current_context.md with both plan paths. Set approach statuses to "pending".

RULES:
- Both plans must target the SAME acceptance criteria — only the approach differs.
- Both plans must be independently executable.
```

---

## Entering Phase 3: Execute

### Context to Load
- `project_memory/current_context.md` (contains the plan, decisions, and step checklist)

### Prompt Template (Normal Mode)

```
I am entering the EXECUTE phase for milestone: "{milestone_name}".

CONTEXT LOADED:
- Active milestone: {milestone_name}
- Plan steps: {step_checklist_from_current_context}
- Key decisions: {key_decisions}
- Known blockers: {blockers_if_any}

GIT CHECK:
- Verify you are on the pf/milestone-{N} branch. If not, check it out.

EXECUTION PROCEDURE:
For each unchecked step in the plan:
1. Implement the change (code, config, docs).
2. Run relevant tests or verification checks.
3. If the step passes: check it off in current_context.md.
4. If the step fails:
   a. Diagnose the failure.
   b. Attempt to fix (up to 2 attempts).
   c. If still failing: record as a blocker in current_context.md and move to the next non-dependent step.
5. Stage and commit completed work incrementally:
   git add <changed-files>
   git commit -m "pf: step {N} — {description}"
   These incremental commits are your safety net. If something breaks, roll back within the milestone.

WHEN BLOCKED:
- Record the blocker clearly: what failed, what was tried, what is needed.
- Skip to the next step that does not depend on the blocker.
- Normal mode: If all remaining steps depend on the blocker, STOP and ask the user.
- Auto mode: If all remaining steps depend on the blocker, attempt an alternative approach. If no alternative works, log the blocker as [AUTO-BLOCKED] in current_context.md and advance to Review with partial completion.
- Continuous mode + unresolvable blocker (e.g., needs API keys): Output <pf-signal>BLOCKED:description</pf-signal> to stop the loop.

RULES:
- Follow the plan. Do not add unplanned work.
- Do not refactor unrelated code.
- Keep commits atomic and well-described.
- If a planned step is unnecessary, skip it and note why.
- Minimize discussion — act as an engineer, produce output.
- Update current_context.md after each completed step.
```

### Prompt Template (Exploratory Mode)

When `exploration_mode: true` in `current_context.md`:

```
I am entering the EXECUTE phase for milestone: "{milestone_name}" in EXPLORATORY MODE.

PARALLEL EXECUTION:
Dispatch TWO Agent subagents simultaneously. Each executes one approach in isolation.

AGENT A:
  subagent_type: "general-purpose"
  isolation: "worktree"
  prompt: |
    You are executing approach A ("{approach_a_slug}") for milestone "{milestone_name}".

    BRANCH: pf/milestone-{N}/a
    PLAN: Read docs/plans/YYYY-MM-DD-{milestone_slug}-approach-a.md
    ACCEPTANCE CRITERIA:
    {acceptance_criteria_list}

    Instructions:
    1. git checkout pf/milestone-{N}/a
    2. Read the plan file listed above
    3. Execute each step in order
    4. After each step: git add <files> && git commit -m "pf: step N — description"
    5. Run tests after each step
    6. When done, report: completed steps, test results, blockers encountered

AGENT B:
  subagent_type: "general-purpose"
  isolation: "worktree"
  prompt: |
    You are executing approach B ("{approach_b_slug}") for milestone "{milestone_name}".

    BRANCH: pf/milestone-{N}/b
    PLAN: Read docs/plans/YYYY-MM-DD-{milestone_slug}-approach-b.md
    ACCEPTANCE CRITERIA:
    {acceptance_criteria_list}

    Instructions:
    1. git checkout pf/milestone-{N}/b
    2. Read the plan file listed above
    3. Execute each step in order
    4. After each step: git add <files> && git commit -m "pf: step N — description"
    5. Run tests after each step
    6. When done, report: completed steps, test results, blockers encountered

AFTER BOTH COMPLETE:
- Update current_context.md with execution summaries from both agents.
- Set approach statuses to "reviewed".
- If one agent failed/crashed, note the failure and proceed with the other.
- Advance to Phase 4 (Review) in exploratory mode.

RULES:
- Do NOT execute the plans yourself — dispatch subagents.
- The orchestrator coordinates; agents implement.
```

---

## Entering Phase 4: Review

### Context to Load
- `project_memory/progress.md` (milestone definitions and acceptance criteria)
- `project_memory/current_context.md` (execution results, completed steps, blockers)
- `project_memory/lessons.md` (prior lessons for comparison)

### Prompt Template (Exploratory Mode)

When `exploration_mode: true` in `current_context.md`, use this template INSTEAD of the normal one:

```
I am entering the REVIEW phase for milestone: "{milestone_name}" in EXPLORATORY MODE.

CONTEXT LOADED:
- Milestone acceptance criteria: {acceptance_criteria_list}
- Approach A ("{approach_a_slug}"): branch pf/milestone-{N}/a — {execution_summary_a}
- Approach B ("{approach_b_slug}"): branch pf/milestone-{N}/b — {execution_summary_b}
- Prior lessons: {lessons_summary}

COMPARATIVE REVIEW PROCEDURE:

1. DISPATCH COMPARATIVE REVIEWER:
   Invoke the reviewer agent in comparative mode:
   - Branch A: pf/milestone-{N}/a
   - Branch B: pf/milestone-{N}/b
   - Acceptance criteria: {acceptance_criteria_list}

2. SELECT WINNER based on comparative review report:
   - Both PASS → pick higher score
   - One PASS, one FAIL → pick the PASS
   - Both PARTIAL → pick more criteria met
   - Both FAIL → pick closer to passing, set exploration_mode to false, re-enter Plan single-branch

3. RECORD DECISION:
   - Update current_context.md: set Winner and Rationale in Exploration Mode section
   - Log: [AUTO-EXPLORE] Selected approach {A/B} ("{slug}") — {rationale}

4. MERGE WINNER TO BASE BRANCH:
   git checkout pf/milestone-{N}
   git merge pf/milestone-{N}/{a_or_b}

5. CONTINUE WITH NORMAL REVIEW (steps 4-11):
   - Skip steps 1-3 (tests/criteria/regressions already checked by comparative reviewer)
   - Continue from step 4 (Update lessons.md) through step 11 (Decide next action)
   - Include in squash commit message: "Chose approach {A/B} over {B/A} because {rationale}"

6. ARCHIVE ALL BRANCHES (after squash-merge, step 9 of normal flow):
   git branch -m pf/milestone-{N} archive/pf/milestone-{N}
   git branch -m pf/milestone-{N}/a archive/pf/milestone-{N}/a
   git branch -m pf/milestone-{N}/b archive/pf/milestone-{N}/b

RULES:
- Trust the comparative reviewer's scoring. Do not re-evaluate criteria.
- Include exploration outcome in lessons.md: which approach won and why.
```

### Prompt Template (Normal Mode)

```
I am entering the REVIEW phase for milestone: "{milestone_name}".

CONTEXT LOADED:
- Milestone acceptance criteria: {acceptance_criteria_list}
- Completed steps: {checked_steps}
- Incomplete steps: {unchecked_steps}
- Blockers encountered: {blockers}
- Prior lessons: {lessons_summary}

REVIEW PROCEDURE:

1. RUN TESTS:
   - Execute the project's test suite.
   - Record: total tests, passed, failed, skipped.
   - If tests fail, note which tests and why.

2. CHECK ACCEPTANCE CRITERIA:
   For each criterion:
   - [ ] {criterion}: MET / NOT MET — {evidence or reason}

3. CHECK FOR REGRESSIONS:
   - Verify that functionality from previous milestones still works.
   - If regressions found: document them as blockers.

4. WRITE LESSONS (append to lessons.md):
   - What worked well in this milestone?
   - What didn't work or took longer than expected?
   - Patterns to reuse in future milestones.
   - Patterns to avoid.

5. UPDATE PROGRESS (update progress.md):
   - If ALL criteria met:
     - Move milestone to "Completed Milestones" with date and summary.
     - Propose 1-3 new upcoming milestones.
     - Re-prioritize the milestone queue.
   - If criteria NOT met:
     - Decide: re-enter Execute (for small gaps) or re-enter Plan (for significant gaps).
     - Note what remains and why.
     - SKIP steps 6-8 (doc-check, squash, archive) — only run on completion.

6. DOC-CHECK AND UPDATE (only if ALL criteria met):
   - Run: git diff --name-only <default-branch>...HEAD
   - Check if any user-facing behavior changed (new commands, APIs, features, workflows).
   - If yes, update relevant docs:
     - README.md: new features, changed usage, new commands
     - CLAUDE.md: changed structure, new conventions, new workflows
     - plugin.json: version bump if features added
     - SKILL.md files: if skill behavior changed
   - Commit: git commit -m "pf: docs — update for milestone {N}"

7. SQUASH-MERGE TO DEFAULT BRANCH (only if ALL criteria met):
   - git checkout <default-branch>
   - git merge --squash pf/milestone-{N}
   - Create squash commit with a rich, structured message.
     Read `current_context.md` "Key Decisions" section and `progress.md` acceptance criteria.
     Use this exact format:

     ```
     Milestone {N}: {milestone_name}

     ## Objective
     {milestone_objective — one sentence from progress.md}

     ## Key Decisions
     - {decision 1 — copy verbatim from current_context.md, include [AUTO] prefix if present}
     - {decision 2}
     - ...

     ## Acceptance Criteria
     - [x] {criterion 1}
     - [x] {criterion 2}
     - ...

     ## Files Changed
     {output of: git diff --stat <default-branch>}

     ## Lessons
     {one-line summary of what worked and what didn't — from lessons.md entry for this milestone}
     ```

     The Key Decisions section is the primary audit trail. Include ALL decisions
     from current_context.md, not just a summary. If a decision was auto-made,
     preserve the [AUTO] tag so the user can identify autonomous choices.

   - Rewrite project_memory/ files to reflect current state (overwrite, not merge).
   - Commit everything together:
     git add -A
     git commit (with the rich message above)

8. UPDATE CHANGELOG:
   - If `CHANGELOG.md` exists at the project root, prepend the new milestone entry.
   - If it does not exist, create it.
   - Format:

     ```
     # Changelog

     ## Milestone {N}: {milestone_name} — {YYYY-MM-DD}
     {milestone_objective — one sentence}

     **Key changes:**
     - {one-line summary per major change, derived from the plan steps}

     **Decisions:**
     - {key decision 1}
     - {key decision 2}

     ---

     ## Milestone {N-1}: {previous milestone} — {date}
     ...
     ```

   - Commit: git add CHANGELOG.md && git commit -m "pf: changelog — milestone {N}"

9. ARCHIVE MILESTONE BRANCH:
   - git branch -m pf/milestone-{N} archive/pf/milestone-{N}
   - The archived branch preserves full incremental commit history.

10. DECIDE NEXT ACTION:
   - If the overall project goal is satisfied:
     - Generate a completion report.
     - STOP the loop.
   - If more milestones remain:
     - Set next milestone as current.
     - Clear current_context.md.
     - Enter Phase 1 (Brainstorm) for the new milestone.

COMPLETION REPORT FORMAT (when goal is satisfied):
- Project goal: {goal}
- Milestones completed: {count}
- Summary of each milestone.
- Lessons learned (highlights).
- Final project state.
- Git log: list of squash-merge commits for all milestones.

CONTINUOUS LOOP SIGNALS (output these when in continuous mode):
- After generating the completion report (goal satisfied):
  Output: <pf-signal>GOAL_COMPLETE</pf-signal>
- If blocked and cannot continue autonomously:
  Output: <pf-signal>BLOCKED:description of why</pf-signal>
- If advancing to the next milestone (goal NOT yet satisfied):
  Do NOT output any signal — the stop hook will re-invoke automatically.

RULES:
- Be honest about criteria. "Met" requires evidence, not assumption.
- Do not skip regression checks.
- Always write lessons, even if everything went smoothly.
- Never skip the doc-check. Undocumented features create debt.
- The squash-merge commit message is the primary audit trail — make it thorough.
- Normal mode: If this milestone has failed review twice, STOP and ask the user.
- Auto mode: If this milestone has failed review twice, re-scope it smaller. If it fails a third time, skip it and log the failure in lessons.md. If skipping, output <pf-signal>BLOCKED:Milestone "{milestone_name}" failed 3 times — requires user intervention</pf-signal>.
```
