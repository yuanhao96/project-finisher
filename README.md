# project-finisher

Ever wish you could hand Claude Code a goal file and walk away while it figures out the architecture, writes the code, tests everything, and keeps going until it's done? That's what this plugin does. You describe what you want, point it at a project, and it runs an iterative loop — brainstorming approaches, planning implementation, writing code, and reviewing its own work — until the goal is met. It remembers where it left off between sessions, so even large projects can be tackled across multiple sittings.

## Workflow Overview

```mermaid
flowchart TD
    START(["/finish --goal goal.md"]) --> CHECK{project_memory/ exists?}
    CHECK -- No --> INIT["Initialize memory Propose 1-3 milestones"]
    CHECK -- Yes --> RESUME["Resume from current phase"]
    INIT --> BRAINSTORM
    RESUME --> BRAINSTORM

    subgraph BRAINSTORM ["Phase 1: Brainstorm"]
        direction TB
        B1["Round 1: Feasibility & approach /scientific-brainstorming"]
        B1 -- "pushback" --> B2["Round 2: Address concerns /scientific-brainstorming"]
        B2 -- "new concerns?" --> B3["Round 3+: Until convergence /scientific-brainstorming"]
        B3 --> BOUT["Re-scope milestone Revise roadmap Record decisions"]
    end

    BRAINSTORM --> PLAN

    subgraph PLAN ["Phase 2: Plan"]
        P1["Create step-by-step plan Files, tasks, tests, dependencies Save to docs/plans/"]
    end

    PLAN --> EXECUTE

    subgraph EXECUTE ["Phase 3: Execute"]
        E1["Implement plan steps Write code + tests Commit after each unit Handle blockers"]
    end

    EXECUTE --> REVIEW

    subgraph REVIEW ["Phase 4: Review"]
        R1["Run test suite Check acceptance criteria Check regressions Update lessons.md Propose new milestones"]
    end

    REVIEW --> DONE{Goal reached?}
    DONE -- "Yes" --> STOP(["Done!"])
    DONE -- "No" --> NEXT["Next milestone"] --> BRAINSTORM

    style BRAINSTORM fill:#e8f4fd,stroke:#4a90d9
    style PLAN fill:#e8fde8,stroke:#4a9950
    style EXECUTE fill:#fdf4e8,stroke:#d9904a
    style REVIEW fill:#f4e8fd,stroke:#904ad9
    style START fill:#333,color:#fff,stroke:#333
    style STOP fill:#333,color:#fff,stroke:#333
```

**Roadmap changes** happen at two points: Brainstorm (re-scope, add prerequisites, split, reorder) and Review (propose new milestones, re-prioritize).

**The plugin stops to ask you** when the goal is ambiguous, approaches are equally viable, external resources are needed, the project has diverged from the goal, or the same milestone has failed twice.

## Prerequisites

This plugin depends on skills from these plugins:

| Plugin | Used In | Purpose |
|--------|---------|---------|
| `scientific-skills@claude-scientific-skills` | Brainstorm phase | `/scientific-brainstorming` for feasibility analysis |
| `superpowers@claude-plugins-official` | Plan phase | `/superpowers:write-plan` for structured implementation plans |

Install them first if you don't already have them:

```bash
claude plugin marketplace add https://github.com/K-Dense-AI/claude-scientific-skills.git
claude plugin install scientific-skills@claude-scientific-skills

claude plugin install superpowers@claude-plugins-official
```

## Installation

```bash
# 1. Register the marketplace
claude plugin marketplace add https://github.com/yuanhao96/project-finisher.git

# 2. Install the plugin
claude plugin install project-finisher@project-finisher

# 3. Restart Claude Code to activate
```

## Usage

Point the plugin at a goal file that describes what you want to build or finish:

```bash
/finish --goal path/to/goal.md
```

To target a specific project directory (defaults to the current working directory):

```bash
/finish --goal path/to/goal.md --project ./my-project
```

The plugin will read your goal, assess the current state of the project, and begin iterating autonomously until the goal is satisfied.

## Memory Files

The plugin persists state across sessions in a `project_memory/` directory at the root of your project:

| File | Purpose |
|------|---------|
| `project_memory/progress.md` | Tracks completed tasks, current phase, and overall progress toward the goal. |
| `project_memory/current_context.md` | Captures the active working context — what was just done, what comes next, and any open questions. |
| `project_memory/lessons.md` | Records lessons learned during execution — things that worked, things that didn't, and decisions made along the way. |

These files are read at the start of each session so the plugin can pick up exactly where it left off.

## License

MIT
