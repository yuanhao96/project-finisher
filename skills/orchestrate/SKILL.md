---
name: orchestrate
description: "This skill should be used when running the project-finisher workflow. Use when the user invokes /finish or when continuing a project-finisher session. Orchestrates the iterative brainstorm/plan/execute/review cycle for autonomous project completion."
version: 0.1.0
---

# Orchestrator Skill

The orchestrator is the central brain of project-finisher. It drives the iterative brainstorm/plan/execute/review loop, manages milestone progression, and coordinates with the memory skill to persist state across sessions.

---

## Startup Procedure

When the orchestrator is invoked, execute the following steps in order:

1. **Read the goal file** — Load the user-provided goal file (passed via `--goal`). This is the immutable source of truth for the project.
2. **Check for existing memory** — Look for a `project_memory/` directory at the project root.
   - **If `project_memory/` exists (resume)**: Read `progress.md` to determine the current milestone and its phase. Read `current_context.md` for active working state. Enter the appropriate phase for the current milestone.
   - **If `project_memory/` does not exist (initialize)**: Create the `project_memory/` directory. Initialize `progress.md`, `current_context.md`, and `lessons.md` using the templates from the memory skill. Extract the goal summary from the goal file into `progress.md`. Propose the first 1-3 milestones based on the goal. Set the first milestone as current and enter the Brainstorm phase.
3. **Identify current milestone and phase** — From `progress.md`, read the current milestone name and phase (brainstorm, plan, execute, or review).
4. **Enter the phase** — Jump to the matching phase in the iteration loop below. Load only the context that phase requires (see the memory skill's reading table).

---

## The Iteration Loop

Each milestone progresses through four phases in order. After the Review phase completes, the loop either advances to the next milestone (starting at Brainstorm) or terminates if the project goal is satisfied.

### Phase 1: Brainstorm

**Purpose**: Validate feasibility and refine the approach for the current milestone through multiple rounds of `/scientific-brainstorming`. Each round surfaces problems; the next round addresses them. Do NOT implement anything.

**Context to load**: goal file + `progress.md` + `lessons.md`

**Procedure**:

1. Summarize the current milestone's objective in the context of the overall goal.
2. Conduct **multiple rounds** of `/scientific-brainstorming`, where each round builds on the pushback from the previous one:

   **Round 1 — Feasibility and approach**:
   - Invoke `/scientific-brainstorming` with: the milestone objective, relevant lessons from `lessons.md`, and the current project state.
   - Ask: Is this milestone feasible as scoped? What are 2-3 candidate approaches? What are the trade-offs?
   - Collect the output: recommended approach, concerns raised, open questions.

   **Round 2 — Address Round 1 pushback**:
   - Take every concern, question, and risk that Round 1 raised.
   - Invoke `/scientific-brainstorming` again, this time focused on resolving those specific issues.
   - Ask: How do we mitigate each risk? Can we answer each open question? Does the recommended approach still hold, or should we pivot?
   - Collect the output: resolved concerns, remaining risks, refined approach.

   **Round 3+ — Continue until convergence** (if needed):
   - If Round 2 surfaced new significant concerns or changed the approach, run another round addressing the new pushback.
   - Stop when a round produces **no new significant risks or questions** — the approach has converged.
   - Typical milestone: 2-3 rounds. Complex or risky milestone: 3-5 rounds. Simple milestone: 2 rounds minimum.

3. After convergence:
   - Re-scope the milestone if brainstorming reveals it is too large, too small, or misdirected. Update `progress.md` if the milestone definition changes.
   - Record **all** key decisions, resolved concerns, and remaining risks in `current_context.md` under "Key Decisions". Include which round produced each decision.
   - Note any unresolved risks that the Plan and Execute phases should watch for.
4. Advance to Phase 2 (Plan).

**Convergence check**: A round has converged when `/scientific-brainstorming` responds with no new concerns, endorses the approach, and the only remaining items are implementation details (not feasibility questions).

**Rules**:
- Do not write code, create files, or make commits during this phase.
- Always run at least 2 rounds — never skip the pushback-resolution cycle.
- If a prior lesson directly applies, feed it into Round 1 explicitly so brainstorming can build on it.
- If the milestone is ambiguous or blocked by unknowns after 3+ rounds, stop and ask the user (see "When to Stop and Ask the User").

---

### Phase 2: Plan

**Purpose**: Produce a concrete, ordered implementation plan that can be executed without further clarification.

**Context to load**: goal file + `progress.md` + `current_context.md`

**Procedure**:

1. Based on the brainstorm decisions in `current_context.md`, create a step-by-step implementation plan covering:
   - **Files to create or modify** — List every file path with a brief description of the change.
   - **Tasks** — Ordered list of discrete work items, each small enough to verify independently.
   - **Tests** — What to test and how (unit tests, integration tests, manual checks).
   - **Dependency order** — Which tasks must complete before others can start.
2. Save the full plan to `docs/plans/YYYY-MM-DD-milestone-name.md` (create the `docs/plans/` directory if it does not exist). Use the current date and a slug of the milestone name.
3. Update `current_context.md`:
   - Set the "Current Phase" to `plan`.
   - Copy the step list into the "Plan Reference > Steps" section as a checklist.
4. Validate the plan: every step must be actionable without asking the user for clarification. If any step requires input, stop and ask.
5. Advance to Phase 3 (Execute).

**Rules**:
- The plan must be self-contained. Another agent reading only `current_context.md` should be able to execute it.
- Each task should touch a small, well-defined scope. If a single task affects more than 5 files, split it.
- Include rollback notes for any risky steps (e.g., database migrations, dependency upgrades).

---

### Phase 3: Execute

**Purpose**: Implement the plan. Write code, create files, run tests, make commits. Act as an engineer — minimize discussion, maximize output.

**Context to load**: `current_context.md` (contains the plan reference and all decisions)

**Procedure**:

1. Work through the steps in `current_context.md` "Plan Reference > Steps" in order.
2. For each step:
   - Implement the change (code, configuration, documentation).
   - Run relevant tests or checks to verify the step.
   - Check off the step in `current_context.md`.
   - Commit the work with a descriptive message if the step represents a logical unit.
3. If blocked on a step:
   - Record the blocker in `current_context.md` under "Blockers".
   - Attempt to resolve it (search for solutions, try alternative approaches).
   - If the blocker cannot be resolved autonomously, note it and continue with non-dependent steps.
   - If all remaining steps depend on the blocker, stop and ask the user.
4. After all steps are complete (or all non-blocked steps are done), advance to Phase 4 (Review).

**Rules**:
- Follow the plan. Do not add unplanned work unless it is strictly necessary to complete a planned step.
- Keep commits atomic and well-described.
- Do not refactor unrelated code during execution.
- If a planned step turns out to be unnecessary, skip it and note why in `current_context.md`.

---

### Phase 4: Review

**Purpose**: Evaluate the milestone against its acceptance criteria. Capture lessons. Decide what comes next.

**Context to load**: `progress.md` + `current_context.md` + `lessons.md`

**Procedure**:

1. **Run tests**: Execute the project's test suite (or the tests defined in the plan). Record pass/fail results.
2. **Check acceptance criteria**: For each criterion in the current milestone's acceptance criteria (from `progress.md`), verify whether it is met. Check the box if met; note why if not.
3. **Check for regressions**: Verify that work from previous milestones still functions correctly.
4. **Update lessons.md**: Append a new section for this milestone with:
   - What worked well.
   - What did not work or took longer than expected.
   - Patterns to reuse in future milestones.
   - Patterns to avoid.
5. **Update progress.md**:
   - If all acceptance criteria are met: Move the milestone to "Completed Milestones" with a date and summary.
   - If criteria are not met: Note what remains and decide whether to re-enter Execute or re-plan.
   - Propose 1-3 new upcoming milestones based on what was learned and what remains toward the goal.
   - Re-prioritize the upcoming milestone queue.
6. **Decide next action**:
   - If the overall project goal is satisfied: Generate a completion report summarizing all milestones, total work done, and final state. Stop the loop.
   - If more milestones remain: Set the next highest-priority milestone as current, reset `current_context.md`, and enter Phase 1 (Brainstorm) for the new milestone.

**Rules**:
- Be honest about acceptance criteria. A criterion is met only if it can be demonstrated, not merely if the code "looks right".
- Do not skip the regression check. If regressions are found, they become blockers for the next milestone or require re-opening the current one.
- Always write lessons, even if the milestone went smoothly. "It went as planned" is itself a useful signal.

---

## Milestone Scoping Rules

Every milestone must satisfy all of the following constraints:

| Rule | Requirement |
|------|-------------|
| **Session-completable** | The milestone must be completable within a single session (one brainstorm/plan/execute/review cycle). |
| **Acceptance criteria** | Must have 2-5 concrete, verifiable acceptance criteria. |
| **File count** | Should touch fewer than 15 files. If more are needed, split the milestone. |
| **Independent value** | The milestone must deliver independently valuable work. After completion, the project should be in a better state than before, even if no further milestones are completed. |
| **Clear boundary** | It must be obvious when the milestone is done. Avoid criteria like "improve performance" — use "reduce page load time to under 2 seconds" instead. |

If a milestone violates these rules during Brainstorm, re-scope it before advancing to Plan.

See `references/milestone-examples.md` for concrete examples of well-scoped and poorly-scoped milestones.

---

## Iteration Progression

As the project advances through milestones, the nature of the work changes. Use this table to guide milestone selection:

| Project Stage | Typical Milestone Focus | Examples |
|---------------|------------------------|----------|
| **Early** (0-20% of goal) | Setup, scaffolding, architecture decisions, core data models | Initialize project structure, set up build system, define database schema, create core abstractions |
| **Middle** (20-80% of goal) | Feature implementation, integrations, business logic | Implement user authentication, build API endpoints, create UI components, add data validation |
| **Later** (80-100% of goal) | Polish, optimization, edge cases, documentation, testing gaps | Add error handling for edge cases, optimize slow queries, write missing tests, improve logging, create user documentation |

**Guidelines**:
- Early milestones should establish foundations that later milestones build upon.
- Middle milestones should deliver visible, testable features.
- Later milestones should harden the project and close gaps. Avoid introducing major new features in later stages.
- If the Review phase repeatedly finds regressions, insert a "stabilization" milestone focused on testing and bug fixes.

---

## When to Stop and Ask the User

The orchestrator should operate autonomously, but must stop and ask the user in these situations:

1. **Ambiguous goal**: The goal file is unclear about what "done" looks like, and multiple reasonable interpretations exist that would lead to fundamentally different work.
2. **Equally viable approaches**: Brainstorming produces two or more approaches with similar trade-offs, and the choice significantly affects the project's direction (e.g., choosing between two frameworks, two database designs).
3. **External resources needed**: The milestone requires API keys, credentials, third-party service access, paid dependencies, or hardware that the orchestrator cannot provision.
4. **Significant divergence from goal**: During Review, it becomes clear that the completed work has drifted meaningfully from the original goal, and course correction requires user input.
5. **Repeated failure**: The same milestone has failed review twice. Something fundamental may be wrong with the approach or the goal itself.

When stopping, provide:
- A clear summary of the situation.
- The specific question or decision needed.
- 2-3 options with trade-offs, if applicable.
- A recommendation, if one option is clearly better.

---

## Phase Reference

See `references/phase-prompts.md` for internal prompt templates used when entering each phase.
