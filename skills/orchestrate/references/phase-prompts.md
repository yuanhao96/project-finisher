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

## Entering Phase 2: Plan

### Context to Load
- Goal file (the user-provided project goal)
- `project_memory/progress.md` (milestone definitions and status)
- `project_memory/current_context.md` (brainstorm decisions, key decisions, open questions)

### Prompt Template

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

2. MILESTONE RUBRIC — For each dimension in Quality Priorities (from goal file):
   - What does 1-3 look like for this milestone? (minimal, broken, missing)
   - What does 7-10 look like? (thorough, complete, exemplary)
   - Base on the planned files, tests, and scope.
   - Include in plan artifact AND current_context.md under ## Milestone Rubric.

3. TASKS — Ordered implementation steps:
   - Each task should be a single, verifiable unit of work.
   - Include the expected outcome for each task.
   - Note which files each task touches.

4. TESTS — What to test and how:
   - Unit tests: what functions/modules to test.
   - Integration tests: what workflows to verify.
   - Manual checks: what to inspect visually or via CLI.

5. DEPENDENCY ORDER — Which tasks must complete before others:
   - Task N must complete before Task M because...

6. ROLLBACK NOTES — For risky steps:
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

---

## Entering Phase 3: Execute

### Context to Load
- `project_memory/current_context.md` (contains the plan, decisions, and step checklist)

### Prompt Template

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

---

## Entering Phase 4: Review

### Context to Load
- `project_memory/progress.md` (milestone definitions and acceptance criteria)
- `project_memory/current_context.md` (execution results, completed steps, blockers)
- `project_memory/lessons.md` (prior lessons for comparison)

### Prompt Template

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

2. SCORE AND IMPROVE THE MILESTONE (inner review-fix loop):

   ROUND 1 — Score each dimension using Quality Scoring procedure:
   a. Load milestone rubric from current_context.md.
   b. Score each dimension (weight > 0) from 1-10 with cited evidence.
   c. Compute weighted average: Σ(weight × score) / Σ(weight).
   d. Write score card to current_context.md under ## Score Cards.

   IF weighted average ≥ threshold → proceed to step 3.

   IF weighted average < threshold → enter fix loop:

   e. STRUCTURAL FAILURE CHECK: If ANY dimension < 4 → break out, re-enter Plan phase.
      Log failing dimension and score in current_context.md.

   f. IDENTIFY FIX TARGETS: Dimensions scoring < 7, prioritized by weight × (7 - score).
      Cap at 3 fixes per round.

   g. IMPLEMENT FIXES: Minimum changes to improve each target dimension.
      Commit: pf: review-fix round N — {description}

   h. RE-SCORE (Round N+1): Score all dimensions again with fresh evidence.
      Write new score card with Delta column.

   i. CHECK EXIT CONDITIONS:
      - Weighted average ≥ threshold → PASS, proceed to step 3.
      - Improvement < 0.5 from previous round → STAGNATION.
        If score ≥ threshold - 1.0: accept with caveats, proceed to step 3.
        Otherwise: re-enter Execute phase.
      - Round count = 3 (MAX_REVIEW_ROUNDS) → MAX ROUNDS.
        If score ≥ threshold - 1.0: accept with caveats, proceed to step 3.
        Otherwise: re-enter Execute phase.

   j. If no exit condition → repeat from (f).

   AFTER LOOP PASSES (threshold met or accepted with caveats):
   - Invoke reviewer agent for independent PASS/FAIL verdict.
   - If reviewer PASS → proceed to step 3.
   - If reviewer FAIL → one additional fix round targeting reviewer's concerns.
     Re-invoke reviewer. If still FAIL, note discrepancy in lessons.md,
     proceed with loop's score as final score.

   Inner loop rounds are sub-iterations — do NOT count against continuous mode budgets.

3. CHECK ACCEPTANCE CRITERIA:
   For each criterion:
   - [ ] {criterion}: MET / NOT MET — {evidence or reason}

4. CHECK FOR REGRESSIONS:
   - Verify that functionality from previous milestones still works.
   - If regressions found: document them as blockers.

5. WRITE LESSONS (append to lessons.md):
   - What worked well in this milestone?
   - What didn't work or took longer than expected?
   - Patterns to reuse in future milestones.
   - Patterns to avoid.

6. UPDATE PROGRESS (update progress.md):
   - If ALL criteria met:
     - Move milestone to "Completed Milestones" with date, summary, and final score.
     - Propose 1-3 new upcoming milestones.
     - Re-prioritize the milestone queue.
   - If criteria NOT met:
     - Decide: re-enter Execute (for small gaps) or re-enter Plan (for significant gaps).
     - Note what remains and why.
     - SKIP steps 7-10 (doc-check, squash, changelog, archive) — only run on completion.

7. DOC-CHECK AND UPDATE (only if ALL criteria met):
   - Run: git diff --name-only <default-branch>...HEAD
   - Check if any user-facing behavior changed (new commands, APIs, features, workflows).
   - If yes, update relevant docs:
     - README.md: new features, changed usage, new commands
     - CLAUDE.md: changed structure, new conventions, new workflows
     - plugin.json: version bump if features added
     - SKILL.md files: if skill behavior changed
   - Commit: git commit -m "pf: docs — update for milestone {N}"

8. SQUASH-MERGE TO DEFAULT BRANCH (only if ALL criteria met):
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

     ## Final Score
     {weighted_average} / 10

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

9. UPDATE CHANGELOG:
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

10. ARCHIVE MILESTONE BRANCH:
   - git branch -m pf/milestone-{N} archive/pf/milestone-{N}
   - The archived branch preserves full incremental commit history.

11. EVOLVE WORKFLOW PREFERENCES:
   - Run the evolve skill's "Observe & Extract" procedure.
   - Update ~/.claude/project-finisher-data/workflow_preferences.md.

12. DECIDE NEXT ACTION:
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
