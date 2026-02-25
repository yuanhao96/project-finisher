# project-finisher

A Claude Code plugin that autonomously drives software projects from a high-level goal to completion through iterative brainstorm/plan/execute/review cycles. It maintains cross-session memory so work can resume seamlessly, breaks complex goals into manageable tasks, executes them, reviews the results, and loops until the project is done.

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

## How It Works — The 4-Phase Cycle

Each iteration runs through four phases:

1. **Brainstorm** — Analyze the goal and the current state of the project. Identify what needs to happen next, surface unknowns, and generate candidate approaches.
2. **Plan** — Select the best approach from the brainstorm output and produce a concrete, ordered list of tasks with acceptance criteria.
3. **Execute** — Carry out the planned tasks: write code, run commands, create files, install dependencies, and wire things together.
4. **Review** — Evaluate what was accomplished against the plan and the original goal. Decide whether the goal is met or another cycle is needed.

The cycle repeats until the review phase confirms the project goal has been fully achieved.

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
