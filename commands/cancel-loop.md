---
name: cancel-loop
description: "Cancel the project-finisher continuous loop"
---

# /cancel-loop Command

Stops the project-finisher continuous loop immediately.

## Behavior

1. Check if `.claude/pf-loop.state.json` exists.
   - **If it exists**: Remove the file and report the total iterations completed.
   - **If it does not exist**: Inform the user that no active loop was found.

2. The next time Claude attempts to exit, the Stop hook will see no state file and allow normal exit.

## Implementation

Run the cancel-loop script:

```bash
bash ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/cancel-loop.sh
```

Report the output to the user.
