---
name: status
description: "Show current project-finisher progress and milestone status"
---

# /status Command

## Check for Active Session

Look for the `project_memory/` directory at the project root.

**If `project_memory/` does not exist**, respond with:

> No project-finisher session found. Use `/finish --goal <path>` to start.

Do not proceed further.

---

## Read Memory Files

If `project_memory/` exists, read both of these files:

- `project_memory/progress.md`
- `project_memory/current_context.md`

---

## Present Status Report

Generate a status report with the following sections:

### Goal Summary

Extract and display the goal summary from the "Goal Summary" section of `progress.md`. Present it as a brief paragraph.

### Current Milestone

Display the current milestone with:
- **Name**: The milestone title
- **Phase**: The current phase (brainstorm, plan, execute, or review)
- **Status**: in-progress or blocked
- **Acceptance criteria**: List each criterion with its checkbox state (checked if met, unchecked if not yet met)

If additional context is useful (e.g., active blockers or plan step progress), include relevant details from `current_context.md`.

### Progress Overview

Show counts:
- **Completed**: [N] milestones
- **In Progress**: 1 (the current milestone)
- **Upcoming**: [M] milestones

### Milestone List

Present all milestones as checkbox lists grouped by status:

**Completed:**
- [x] Milestone name 1 (completed YYYY-MM-DD)
- [x] Milestone name 2 (completed YYYY-MM-DD)

**In Progress:**
- [ ] Current milestone name (phase: [current phase])

**Upcoming:**
- [ ] Upcoming milestone 1 (priority: [priority])
- [ ] Upcoming milestone 2 (priority: [priority])

---

## Notes

- This command is read-only. It does not modify any memory files.
- If any memory file is missing or malformed, report what could be read and note what is missing rather than failing silently.
