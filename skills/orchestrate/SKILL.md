---
name: orchestrate
description: "This skill should be used when running the project-finisher workflow. Use when the user invokes /finish or when continuing a project-finisher session. Orchestrates the iterative brainstorm/plan/execute/review cycle for autonomous project completion."
version: 0.1.0
---

# Orchestrator Skill

The orchestrator is the central brain of project-finisher. It drives the iterative brainstorm/plan/execute/review loop, manages milestone progression, coordinates with the memory skill to persist state across sessions, and uses git for version control, rollback, and auditability.

---

## Startup Procedure

When the orchestrator is invoked, execute the following steps in order:

1. **Read the goal file** — Load the user-provided goal file (passed via `--goal`). This is the immutable source of truth for the project.
2. **Load workflow preferences** — Read `~/.claude/project-finisher-data/workflow_preferences.md` if it exists. This file contains learned user behavior patterns (pacing, depth, workflow ordering, tool preferences, edit size, error recovery, interaction patterns) that adapt how the orchestrator operates. Apply the adaptations described in the evolve skill's "Apply Procedure" throughout this session. If the file does not exist, use default behavior (no adaptations).
3. **Initialize git repository** — Check if the target project has a git repository (`git rev-parse --git-dir`).
   - **If no git repo exists**: Run `git init`. Create a `.gitignore` with at minimum: `.claude/`, `.DS_Store`, `__pycache__/`, `*.pyc`, `node_modules/`, `.env`. Make an initial commit with the existing project files (or an empty initial commit if the project is new).
   - **If a git repo exists**: Record the default branch name (e.g., `main`, `master`) for later use. Ensure the working tree is clean — if there are uncommitted changes, warn the user and suggest committing or stashing before proceeding.
4. **Check for existing memory** — Look for a `project_memory/` directory at the project root.
   - **If `project_memory/` exists (resume)**: Read `progress.md` to determine the current milestone and its phase. Read `current_context.md` for active working state. Enter the appropriate phase for the current milestone.
   - **If `project_memory/` does not exist (initialize)**: Create the `project_memory/` directory. Initialize `progress.md`, `current_context.md`, and `lessons.md` using the templates from the memory skill. Extract the goal summary from the goal file into `progress.md`. Propose the first 1-3 milestones based on the goal. Set the first milestone as current and enter the Brainstorm phase.
5. **Identify current milestone and phase** — From `progress.md`, read the current milestone name and phase (brainstorm, plan, execute, or review).
6. **Enter the phase** — Jump to the matching phase in the iteration loop below. Load only the context that phase requires (see the memory skill's reading table).

---

## The Iteration Loop

Each milestone progresses through four phases in order. After the Review phase completes, the loop either advances to the next milestone (starting at Brainstorm) or terminates if the project goal is satisfied.

### Phase 1: Brainstorm

**Purpose**: Validate feasibility and refine the approach for the current milestone through multiple rounds of `/scientific-brainstorming`. Each round surfaces problems; the next round addresses them. Do NOT implement anything.

**Context to load**: goal file + `progress.md` + `lessons.md`

**Git actions at phase start**:
1. Determine the milestone number (count of completed milestones + 1).
2. Check if `pf/milestone-N` already exists (session resume):
   - **If yes**: Check it out (`git checkout pf/milestone-N`) and continue where you left off.
   - **If no**: Create and checkout a new branch off the default branch (`git checkout -b pf/milestone-N <default-branch>`).
3. If the default branch has new commits since the last milestone (e.g., user made manual changes), merge the default branch into the milestone branch: `git merge <default-branch>`. If merge conflicts occur, output `<pf-signal>BLOCKED:Merge conflict with user changes on default branch — manual resolution needed</pf-signal>` and stop.

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

3. After convergence, **update the current milestone and roadmap**:
   - **Re-scope current milestone** if brainstorming reveals it is too large, too small, or misdirected. Update the milestone definition and acceptance criteria in `progress.md`.
   - **Revise the roadmap** if brainstorming revealed any of the following:
     - A prerequisite milestone is needed that wasn't previously identified → add it to Upcoming Milestones and re-prioritize.
     - The current milestone should be split into multiple smaller milestones → replace it with the first piece and queue the rest.
     - Upcoming milestones need reordering due to newly discovered dependencies → update priorities and dependency chains.
     - An upcoming milestone is no longer needed or has been absorbed by this one → remove or merge it.
   - Record **all** key decisions, resolved concerns, and remaining risks in `current_context.md` under "Key Decisions". Include which round produced each decision.
   - Note any unresolved risks that the Plan and Execute phases should watch for.
4. Advance to Phase 2 (Plan).

**Convergence check**: A round has converged when `/scientific-brainstorming` responds with no new concerns, endorses the approach, and the only remaining items are implementation details (not feasibility questions).

**Rules**:
- Do not write code or create project files during this phase. The only commits allowed are `project_memory/` updates (brainstorm decisions).
- Always run at least 2 rounds — never skip the pushback-resolution cycle.
- If a prior lesson directly applies, feed it into Round 1 explicitly so brainstorming can build on it.
- If the milestone is ambiguous or blocked by unknowns after 3+ rounds, stop and ask the user (see "When to Stop and Ask the User").
- **Auto mode**: When `/scientific-brainstorming` presents multiple candidate approaches or options to choose from, do NOT stop to ask the user. Instead, evaluate the options using this priority:
  1. Pick the option that brainstorming explicitly recommends (look for words like "recommended", "preferred", "best option").
  2. If no explicit recommendation, pick the option with the best trade-off profile (lowest risk, fewest dependencies, best alignment with goal).
  3. If options are genuinely equivalent, pick the simplest one.
  4. Log the decision as `[AUTO]` in `current_context.md` and continue to the next brainstorming round with the chosen approach.

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
2. **Generate milestone rubric** — For each dimension in the project's Quality Priorities (from the goal file), write concrete descriptors for this specific milestone:
   - What does 1-3 look like? (minimal, broken, or missing)
   - What does 7-10 look like? (thorough, complete, or exemplary)
   - Base descriptors on the planned files, tests, and scope — be specific to what this milestone is building.
   - Include the rubric table in the plan artifact (`docs/plans/`) and in `current_context.md` under a `## Milestone Rubric` section. Use the format defined in the Quality Scoring section.
3. Save the full plan to `docs/plans/YYYY-MM-DD-milestone-name.md` (create the `docs/plans/` directory if it does not exist). Use the current date and a slug of the milestone name.
4. Update `current_context.md`:
   - Set the "Current Phase" to `plan`.
   - Copy the step list into the "Plan Reference > Steps" section as a checklist.
5. Validate the plan: every step must be actionable without asking the user for clarification. If any step requires input, stop and ask.
6. Advance to Phase 3 (Execute).

**Rules**:
- The plan must be self-contained. Another agent reading only `current_context.md` should be able to execute it.
- Each task should touch a small, well-defined scope. If a single task affects more than 5 files, split it.
- Include rollback notes for any risky steps (e.g., database migrations, dependency upgrades).

---

### Phase 3: Execute

**Purpose**: Implement the plan. Write code, create files, run tests, make commits. Act as an engineer — minimize discussion, maximize output.

**Context to load**: `current_context.md` (contains the plan reference and all decisions)

**Procedure**:

1. Ensure you are on the `pf/milestone-N` branch. If not, check it out.
2. Work through the steps in `current_context.md` "Plan Reference > Steps" in order.
3. For each step:
   - Implement the change (code, configuration, documentation).
   - Run relevant tests or checks to verify the step.
   - Check off the step in `current_context.md`.
   - **Commit incrementally**: After each logical unit of work, create a commit on the milestone branch with a descriptive message (e.g., `pf: step 3 — add authentication middleware`). These incremental commits provide a safety net during execution. If something breaks, you can roll back to the last good commit within the milestone.
4. If blocked on a step:
   - Record the blocker in `current_context.md` under "Blockers".
   - Attempt to resolve it using the error-recovery preference from `workflow_preferences.md`:
     - **retry**: Try alternative approaches quickly, minimize diagnostic steps.
     - **investigate**: Read error output carefully, check related files before retrying.
     - **mixed**: Adapt to the specific error context.
   - If the blocker cannot be resolved autonomously, note it and continue with non-dependent steps.
   - If all remaining steps depend on the blocker, stop and ask the user.
5. After all steps are complete (or all non-blocked steps are done), advance to Phase 4 (Review).

**Rules**:
- Follow the plan. Do not add unplanned work unless it is strictly necessary to complete a planned step.
- Keep commits atomic and well-described. Prefix commit messages with `pf:` for traceability.
- Do not refactor unrelated code during execution.
- If a planned step turns out to be unnecessary, skip it and note why in `current_context.md`.
- Apply the edit-size preference from `workflow_preferences.md`:
  - **incremental**: Use Edit for targeted changes. Break large modifications into multiple small edits.
  - **large-rewrite**: Use Write for comprehensive changes. Batch related modifications.
  - **mixed**: Choose Edit vs Write based on change scope.
- Apply the interaction-pattern preference:
  - **cautious**: Always read files before editing. Explore surrounding code for context.
  - **direct**: Read only the target file before editing.

---

### Phase 4: Review

**Purpose**: Evaluate the milestone against its acceptance criteria. Capture lessons. Update docs. Squash-merge and archive the milestone branch. Decide what comes next.

**Context to load**: `progress.md` + `current_context.md` + `lessons.md`

**Procedure**:

1. **Run tests**: Execute the project's test suite (or the tests defined in the plan). Record pass/fail results.
2. **Score the milestone** using the Quality Scoring procedure:
   a. Load the milestone rubric from `current_context.md` (generated during Phase 2: Plan).
   b. Score each dimension (weight > 0) from 1-10 with cited evidence. Use the rubric descriptors to calibrate.
   c. Compute the weighted average.
   d. Write the score card to `current_context.md` under `## Score Cards` (append as Round 1).
   e. If weighted average ≥ threshold: proceed to step 3.
   f. If weighted average < threshold: note the score and proceed — the inner review-fix loop (if implemented) will handle iterative improvement. Otherwise, the acceptance criteria check in step 3 remains the primary gate.
3. **Check acceptance criteria**: For each criterion in the current milestone's acceptance criteria (from `progress.md`), verify whether it is met. Check the box if met; note why if not.
4. **Check for regressions**: Verify that work from previous milestones still functions correctly.
5. **Update lessons.md**: Append a new section for this milestone with:
   - What worked well.
   - What did not work or took longer than expected.
   - Patterns to reuse in future milestones.
   - Patterns to avoid.
6. **Update progress.md**:
   - If all acceptance criteria are met: Move the milestone to "Completed Milestones" with a date, summary, and **final score** (weighted average from the last scoring round).
   - If criteria are not met: Note what remains and decide whether to re-enter Execute or re-plan. Skip steps 7-10 (doc-check, squash, changelog, archive) — they only run on milestone completion.
   - Propose 1-3 new upcoming milestones based on what was learned and what remains toward the goal.
   - Re-prioritize the upcoming milestone queue.
7. **Doc-check and update** (only if acceptance criteria are all met):
   - Scan which files were modified during this milestone (`git diff --name-only <default-branch>...HEAD`).
   - Determine if any user-facing behavior changed (new commands, changed APIs, new features, modified workflows).
   - If yes, update the relevant documentation:
     | Doc | Update when... |
     |-----|---------------|
     | **README.md** | New user-facing feature, changed usage, new commands |
     | **CLAUDE.md** | Changed project structure, new conventions, new workflows |
     | **plugin.json** | Version bump if milestone adds features |
     | **SKILL.md files** | Skill behavior changed |
   - Commit doc updates on the milestone branch: `pf: docs — update for milestone N`.
8. **Squash-merge to default branch** (only if acceptance criteria are all met):
   - Switch to the default branch: `git checkout <default-branch>`.
   - Squash-merge the milestone branch: `git merge --squash pf/milestone-N`.
   - Create a single commit with a structured message containing (see `references/phase-prompts.md` for exact format):
     - **Objective**: One-sentence milestone objective
     - **Key Decisions**: ALL decisions from `current_context.md`, verbatim, preserving `[AUTO]` tags
     - **Acceptance Criteria**: Checkboxes showing all criteria passed
     - **Final Score**: Weighted average from the last scoring round
     - **Files Changed**: Output of `git diff --stat`
     - **Lessons**: One-line summary from `lessons.md`
   - Rewrite `project_memory/` files on the default branch to reflect the current state (overwrite, not merge — these are state files, history is in git).
   - Stage and commit everything together.
9. **Update CHANGELOG.md**:
   - If `CHANGELOG.md` exists at the project root, prepend the new milestone entry.
   - If it does not exist, create it.
   - Each entry includes: milestone name, date, objective, key changes (from plan steps), and key decisions.
   - Commit: `pf: changelog — milestone N`.
10. **Archive milestone branch**: Rename the milestone branch: `git branch -m pf/milestone-N archive/pf/milestone-N`. Archived branches preserve the full incremental commit history.
11. **Evolve workflow preferences**: Run the evolve skill's "Observe & Extract" procedure. Reflect on this session's pacing, depth, workflow ordering, tool usage patterns, edit size patterns, error recovery behavior, and interaction patterns. Update `~/.claude/project-finisher-data/workflow_preferences.md` with any new observations. This step ensures the orchestrator continuously adapts to the user's working style.
12. **Decide next action**:
    - **If more milestones remain in the queue**: Set the next highest-priority milestone as current, reset `current_context.md`, and enter Phase 1 (Brainstorm) for the new milestone.
    - **If no milestones remain — check goal satisfaction**: Re-read the goal file (the original, immutable goal). For each requirement in the goal file, check whether it has been demonstrably satisfied by the completed milestones. Only consider a requirement satisfied if there is concrete evidence (implemented code, passing tests, working feature).
      - **Goal genuinely satisfied** (all requirements met): Generate a completion report summarizing all milestones, total work done, and final state. Output `<pf-signal>GOAL_COMPLETE</pf-signal>`. Stop the loop.
      - **Goal NOT fully satisfied** (requirements remain): Identify the specific unmet requirements. Propose 1-3 new milestones targeting those gaps, following the milestone scoping rules. Write them to `progress.md` under "Upcoming Milestones". Set the first new milestone as current, reset `current_context.md`, and enter Phase 1 (Brainstorm).

**Rules**:
- Be honest about acceptance criteria. A criterion is met only if it can be demonstrated, not merely if the code "looks right".
- Do not skip the regression check. If regressions are found, they become blockers for the next milestone or require re-opening the current one.
- Always write lessons, even if the milestone went smoothly. "It went as planned" is itself a useful signal.
- Always run the evolve step — behavioral observation is what makes the workflow self-improving.
- Never skip the doc-check. Undocumented features create debt for future milestones.
- The squash-merge commit message is the primary audit trail — make it thorough.

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

## Quality Scoring

The quality scoring system evaluates milestones on multiple dimensions with numeric scores (1-10), providing richer feedback than binary pass/fail. Scores are weighted by user-defined priorities and compared against a threshold to determine milestone completion.

### Quality Priorities Format

The goal file may contain a `## Quality Priorities` section that defines dimension weights and threshold:

```markdown
## Quality Priorities

| Dimension | Weight |
|-----------|--------|
| acceptance_criteria | 4 |
| correctness | 3 |
| test_coverage | 2 |
| code_quality | 2 |
| documentation | 1 |
| performance | 0 |

threshold: 7.0
```

Weights range from 0 (skip) to 4 (critical). If no Quality Priorities section exists, see the `/finish` command for initialization behavior.

### Universal Dimensions

| Dimension | Description | Required? |
|-----------|-------------|-----------|
| `acceptance_criteria` | Are the milestone's acceptance criteria met with evidence? | Yes (weight ≥ 3) |
| `correctness` | Does the implementation work correctly? No regressions from prior milestones? | Yes (weight ≥ 1) |
| `test_coverage` | Are there sufficient tests? Are error/edge cases covered? | Yes (weight ≥ 0) |
| `code_quality` | Does the code follow existing patterns? Is it clean and maintainable? | Yes (weight ≥ 0) |
| `documentation` | Are docs updated for user-facing changes? | Optional (weight 0 to skip) |
| `performance` | Does the implementation meet performance requirements? | Optional (weight 0 to skip) |

### Scoring Procedure

When scoring a milestone (called from Phase 4: Review):

1. Load the milestone rubric from `current_context.md` (generated during Phase 2: Plan).
2. For each dimension with weight > 0, assign a score from 1-10:
   - Use the rubric descriptors to calibrate: match current state against the 1-3 and 7-10 descriptions.
   - **Cite specific evidence** for every score. No score without a citation. Examples:
     - "test_coverage: 6 — 8 tests added covering happy path, missing error tests for timeout and auth failure (see `tests/test_auth.py`)"
     - "correctness: 9 — all 14 tests pass, manual check of edge cases confirms no regressions (`git diff main...HEAD` shows no changes to prior milestone files)"
3. Compute weighted average: `Σ(weight × score) / Σ(weight)`.
4. Compare against threshold (default 7.0, configurable in Quality Priorities).

### Score Card Format

Score cards are written to `current_context.md` under `## Score Cards`:

```markdown
### Round N (YYYY-MM-DD)

| Dimension | Weight | Score | Evidence | Delta |
|-----------|--------|-------|----------|-------|
| acceptance_criteria | 4 | 8 | 3/3 criteria verified ✓ | — |
| correctness | 3 | 7 | All tests pass, no regressions | — |
| test_coverage | 2 | 5 | Missing error path tests for X | — |
| code_quality | 2 | 8 | Follows existing patterns | — |

**Weighted average**: 6.8 / 10 (threshold: 7.0)
```

The Delta column shows change from previous round (`—` for Round 1, `+N` or `-N` for subsequent rounds). All rounds are kept for trajectory visibility.

### Default Weights

When no Quality Priorities section exists and auto mode must infer:

| Dimension | Default Weight |
|-----------|---------------|
| acceptance_criteria | 4 |
| correctness | 3 |
| test_coverage | 2 |
| code_quality | 2 |
| documentation | 1 |
| performance | 0 |

### Auto-Inference Rules

In auto mode, adjust defaults based on keywords found in the goal file:

| Keywords in goal file | Adjustment |
|-----------------------|------------|
| "robust", "production", "reliable", "critical" | correctness → 4, test_coverage → 3 |
| "prototype", "MVP", "proof of concept", "experiment" | test_coverage → 1, code_quality → 1 |
| "documentation", "user-facing", "API" | documentation → 2 or 3 |
| "performance", "latency", "throughput", "scale" | performance → 2 or 3 |
| "refactor", "clean", "maintainable" | code_quality → 3 |

Apply at most one adjustment per dimension. If multiple keywords match, use the highest weight.

### Review-Fix Loop Constants

| Constant | Default | Description |
|----------|---------|-------------|
| `MAX_REVIEW_ROUNDS` | 3 | Maximum scoring rounds per milestone review |
| `STAGNATION_THRESHOLD` | 0.5 | Minimum weighted average improvement between rounds to continue |
| `STRUCTURAL_FAILURE_THRESHOLD` | 4 | Any dimension scoring below this triggers re-plan instead of fix |
| `MAX_FIXES_PER_ROUND` | 3 | Maximum fix targets per round (prevents thrashing) |

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

The orchestrator should operate autonomously, but must stop and ask the user in these situations — **unless auto mode is active** (see "Auto Mode Behavior" below):

1. **Ambiguous goal**: The goal file is unclear about what "done" looks like, and multiple reasonable interpretations exist that would lead to fundamentally different work.
2. **Equally viable approaches**: Brainstorming produces two or more approaches with similar trade-offs, and the choice significantly affects the project's direction (e.g., choosing between two frameworks, two database designs).
3. **External resources needed**: The milestone requires API keys, credentials, third-party service access, paid dependencies, or hardware that the orchestrator cannot provision.
4. **Significant divergence from goal**: During Review, it becomes clear that the completed work has drifted meaningfully from the original goal, and course correction requires user input.
5. **Repeated failure**: The same milestone has failed review twice. Something fundamental may be wrong with the approach or the goal itself.

When stopping (in normal mode), provide:
- A clear summary of the situation.
- The specific question or decision needed.
- 2-3 options with trade-offs, if applicable.
- A recommendation, if one option is clearly better.

### Auto Mode Behavior

When **auto mode** is active (passed from the `/finish --auto` command), the orchestrator resolves decision points autonomously instead of stopping:

| Situation | Auto Mode Action |
|-----------|-----------------|
| **Ambiguous goal** | Choose the interpretation most consistent with the goal file's explicit requirements. Prefer the narrower scope. Document the interpretation in `current_context.md`. |
| **Equally viable approaches** | Apply the decision logic: (1) pick the option with lower risk/complexity, (2) follow the `/scientific-brainstorming` recommendation if one exists, (3) if truly equal, pick the simplest/most conventional approach. Document the choice and reasoning. |
| **External resources needed** | **Still stop and ask** — auto mode cannot provision credentials or external services. |
| **Significant divergence** | Re-align toward the goal by choosing the correction that requires the least rework. Document what diverged and how it was corrected. |
| **Repeated failure** | Re-scope the milestone to a smaller, more achievable version. Split off the harder parts as a separate future milestone. If the milestone has failed 3 times, skip it and move on, logging the failure in `lessons.md`. |

**Logging requirement**: Every auto-decided choice must be logged in `current_context.md` under "Key Decisions" with the prefix `[AUTO]` so the user can review all autonomous decisions after the session. Example:
> `[AUTO] Chose approach A (file-based caching) over approach B (Redis) — simpler, no external dependency, sufficient for the current scale. Brainstorming Round 1 recommended this approach.`

---

## Continuous Loop Signals

When operating in **continuous mode** (`.claude/pf-loop.state.json` exists), the orchestrator must output exit signals at specific points so the Stop hook knows when to end the loop.

### Signal Format

Signals are XML tags in the assistant's output: `<pf-signal>SIGNAL</pf-signal>`

### Available Signals

| Signal | When to Output | Effect |
|--------|---------------|--------|
| `<pf-signal>GOAL_COMPLETE</pf-signal>` | All milestones are completed and the project goal is fully satisfied. Output this in the Review phase after confirming goal satisfaction. | Loop ends cleanly. State file removed. |
| `<pf-signal>BLOCKED:reason</pf-signal>` | The workflow cannot continue autonomously. Examples: external credentials needed, repeated failure (3+ times on same milestone), ambiguous goal that auto mode cannot resolve. | Loop ends. User sees the reason. |

### Rules

- **Always output GOAL_COMPLETE** when the completion report is generated in Phase 4 and the goal file's requirements are all genuinely satisfied. Do not let the session end without the signal — the hook needs it to know the loop is done. Note: milestones running out does NOT mean the goal is complete — if requirements remain unmet, propose new milestones instead.
- **Output BLOCKED** as early as possible when a true blocker is identified. Do not waste iterations trying to work around something that requires user input.
- **Do not output signals prematurely**. Completing a single milestone is NOT goal completion — only output GOAL_COMPLETE when the entire project goal is satisfied.
- **Between milestones**, do not output any signal. The hook will re-invoke the workflow, which will read `progress.md` and continue with the next milestone naturally.
- If continuous mode is not active (no `.claude/pf-loop.state.json`), signals are ignored. It is safe to always include them.

---

## Version Control Strategy

Project-finisher uses git for rollback, auditability, and milestone isolation. This section summarizes the git workflow.

### Branch Model

```
<default-branch> ─── squash merge ─── squash merge ─── ...
  \                    ↑                  ↑
   pf/milestone-1 ────┘   pf/milestone-2 ┘
   (archived after)        (archived after)
```

- Each milestone gets a dedicated branch: `pf/milestone-N`.
- Branches are created off the default branch at the start of Phase 1 (Brainstorm).
- All work (brainstorm decisions, plan, code, docs) is committed to the milestone branch.
- On milestone completion, the branch is squash-merged into the default branch.
- After merge, branches are renamed to `archive/pf/milestone-N` for future reference.

### Commit Strategy

| Phase | Commit behavior |
|-------|----------------|
| Brainstorm | Commit `project_memory/` updates after convergence |
| Plan | Commit plan file + `project_memory/` updates |
| Execute | Incremental commits after each logical step (prefixed with `pf:`) |
| Review | Commit doc updates, then squash-merge everything to default branch |

### Conflict Handling

- Before starting a new milestone, merge the default branch into the milestone branch (not rebase).
- If merge conflicts arise, output `BLOCKED` and let the user resolve.
- Never rebase — it rewrites history and can cause divergence with remotes.

### Rollback

- **Undo an entire milestone**: `git revert <squash-merge-commit>` on the default branch.
- **Inspect incremental history**: Check out `archive/pf/milestone-N` to see step-by-step commits.
- **Undo a single step during execute**: `git revert HEAD` on the milestone branch.

### State Files

`project_memory/` files are **rewritten** (not merged) on each milestone completion. They represent current state. Historical state is preserved in the archived milestone branches and in the squash-merge commit messages.

---

## Phase Reference

See `references/phase-prompts.md` for internal prompt templates used when entering each phase.
