---
name: workflow:refresh
description: Rebuild or incrementally update the repo graph.
---

You are running the **workflow:refresh** slash command.

Inputs:
- `$ARGUMENTS` may contain `--full` to force a full rebuild.

## Procedure

1. Run `workflow refresh` (or `workflow refresh --full` if requested) via Bash.
2. Tell the user how many files were indexed and that the graph is up to date.
3. If the last run was `done` or `failed`, note that the graph now reflects its changes and the next `/workflow:task` will plan against the new state.

Do not mutate any run state.
