# Phase Prompt Templates

These are the internal prompt templates the orchestrator uses when entering each phase of the iteration loop. Each template specifies what context to load and what questions to work through.

---

## Entering Phase 1: Brainstorm

### Context to Load
- Goal file (the user-provided project goal)
- `project_memory/progress.md` (completed milestones, current milestone, upcoming queue)
- `project_memory/lessons.md` (all lessons from prior milestones)

### Prompt Template

```
I am entering the BRAINSTORM phase for milestone: "{milestone_name}".

CONTEXT LOADED:
- Goal: {goal_summary}
- Completed milestones: {list_of_completed_milestones}
- Current milestone objective: {milestone_objective}
- Relevant lessons from prior work: {applicable_lessons}

ROUND 1 — SCOPING AND APPROACH:
1. What exactly does this milestone need to accomplish?
2. What are the inputs and outputs?
3. What are 2-3 possible approaches?
4. What are the trade-offs between them?
5. Are there lessons from prior milestones that apply here?
6. What is the simplest approach that satisfies the acceptance criteria?

ROUND 2 — RISKS AND DEPENDENCIES (if needed):
1. What could go wrong with the chosen approach?
2. What dependencies does this milestone have on external systems, libraries, or prior work?
3. Are there unknowns that must be resolved before planning?
4. Does this milestone's scope still fit within the scoping rules (single session, 2-5 criteria, <15 files, independent value)?

DECISIONS TO RECORD:
- Chosen approach and why.
- Any scope adjustments made.
- Risks acknowledged and mitigation strategies.
- Open questions to carry into planning.

RULES:
- Do NOT write code or create files.
- If the milestone is ambiguous, STOP and ask the user.
- If lessons.md contains a directly relevant lesson, reference it explicitly.
```

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

RULES:
- The plan must be self-contained and executable without clarification.
- If any step requires user input, STOP and ask before finalizing.
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

EXECUTION PROCEDURE:
For each unchecked step in the plan:
1. Implement the change (code, config, docs).
2. Run relevant tests or verification checks.
3. If the step passes: check it off in current_context.md.
4. If the step fails:
   a. Diagnose the failure.
   b. Attempt to fix (up to 2 attempts).
   c. If still failing: record as a blocker in current_context.md and move to the next non-dependent step.
5. Commit completed work with a descriptive message.

WHEN BLOCKED:
- Record the blocker clearly: what failed, what was tried, what is needed.
- Skip to the next step that does not depend on the blocker.
- If all remaining steps depend on the blocker, STOP and ask the user.

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

6. DECIDE NEXT ACTION:
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

RULES:
- Be honest about criteria. "Met" requires evidence, not assumption.
- Do not skip regression checks.
- Always write lessons, even if everything went smoothly.
- If this milestone has failed review twice, STOP and ask the user.
```
