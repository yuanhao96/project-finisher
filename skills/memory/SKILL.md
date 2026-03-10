---
name: memory
description: This skill should be used when managing project-finisher memory files (progress.md, current_context.md, lessons.md). Use when starting a session, completing a milestone, or updating project state. Provides file formats and read/write procedures for the markdown-based memory system.
version: 0.1.0
---

# Project Finisher Memory System

## Memory Directory

All memory files live in `project_memory/` at the target project root.

## Files

| File | Purpose | When to Update |
|------|---------|----------------|
| `progress.md` | Milestone queue with status | After each review phase |
| `current_context.md` | Active milestone details, decisions, blockers | During execution, cleared on milestone completion |
| `lessons.md` | What worked, what failed, patterns discovered | After each review phase |

The goal file is provided by the user and treated as immutable input.

## Initialization

On first run, create `project_memory/` and initialize all three files. Read the goal file to populate the first entry in progress.md.

## Reading Memory

At the start of each phase, load only what that phase needs:

| Phase | Reads |
|-------|-------|
| Brainstorm | goal file + progress.md + lessons.md |
| Plan | goal file + progress.md + current_context.md |
| Execute | current_context.md (contains the plan reference) |
| Review | progress.md + current_context.md + lessons.md |

## Writing Memory

- **progress.md**: Update milestone status, append new proposed milestones
- **current_context.md**: Replace entirely when starting a new milestone
- **lessons.md**: Append new entries after each review

### On Milestone Completion (squash-merge)

When a milestone is squash-merged to the default branch, `project_memory/` files are **rewritten** (overwritten) on the default branch to reflect the current state. This avoids merge conflicts since every milestone branch touches these files. Historical state is preserved in:
- The archived milestone branches (`archive/pf/milestone-N`)
- The squash-merge commit messages (which include decisions and criteria)

See references/file-formats.md for exact templates.
