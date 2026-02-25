# Memory File Format Reference

This document contains the exact templates for all three memory files in `project_memory/`. Claude should use these templates when initializing or updating memory files.

---

## progress.md

```markdown
# Project Progress

## Goal Summary

<!-- One-paragraph summary of the project goal, extracted from the user's goal file. -->

## Completed Milestones

### Milestone: <name>
- **Status**: completed
- **Date completed**: YYYY-MM-DD
- **Summary**: <one-sentence description of what was accomplished>
- **Acceptance criteria met**:
  - [x] <criterion 1>
  - [x] <criterion 2>

<!-- Repeat for each completed milestone. Newest at the bottom. -->

## Current Milestone

### Milestone: <name>
- **Status**: in-progress | blocked
- **Acceptance criteria**:
  - [ ] <criterion 1>
  - [ ] <criterion 2>
- **Phase**: brainstorm | plan | execute | review

## Upcoming Milestones

### Milestone: <name>
- **Priority**: high | medium | low
- **Depends on**: <milestone name or "none">
- **Rough scope**: <one-sentence description>

<!-- Repeat for each upcoming milestone. Ordered by priority then dependency. -->
```

---

## current_context.md

```markdown
# Current Context

## Active Milestone

**Name**: <milestone name>
**Goal**: <what this milestone achieves, in one sentence>

## Current Phase

**Phase**: brainstorm | plan | execute | review
**Started**: YYYY-MM-DD

## Key Decisions

<!-- Decisions made during this milestone that affect implementation. -->

- <decision 1>: <rationale>
- <decision 2>: <rationale>

## Blockers

<!-- Anything preventing progress. Remove items as they are resolved. -->

- [ ] <blocker description>

## Plan Reference

<!-- During the plan phase, the full plan is written here. During execute, this serves as the work checklist. -->

### Steps

1. [ ] <step description>
2. [ ] <step description>
3. [ ] <step description>

## Notes

<!-- Freeform notes, observations, or context that doesn't fit above. -->
```

---

## lessons.md

```markdown
# Lessons Learned

## Milestone: <name> (YYYY-MM-DD)

### What Worked
- <observation>
- <observation>

### What Didn't Work
- <observation>
- <observation>

### Patterns to Reuse
- <pattern>: <why it works>

### Patterns to Avoid
- <pattern>: <why it fails>

<!-- Repeat this entire section for each completed milestone. Newest at the bottom. -->
```
