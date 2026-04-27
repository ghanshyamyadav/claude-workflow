---
name: workflow:status
description: Show the current run (if any) and recent runs.
---

You are running the **workflow:status** slash command.

1. Run `workflow status` via Bash and print its output verbatim.
2. If the user asks for more detail on a specific run, read `.workflow/runs/<id>/state.json` and summarize steps with their status.

Do not mutate any state.
