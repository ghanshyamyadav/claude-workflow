---
name: workflow:replan
description: Throw out the current plan and start over with lessons learned.
---

You are running the **workflow:replan** slash command.

Inputs:
- `$ARGUMENTS` may contain a specific `run_id`.

## Procedure

1. Identify the run. If `run_id` was passed, use it; else find the current run with `workflow status`.
2. Read `.workflow/runs/<id>/task.md`, the existing `plan.json` (will be archived by the CLI), and the latest failing step's `output.txt` and `validate.log`.
3. Briefly tell the user what went wrong under the old plan — one or two sentences.
4. Run:

   ```
   workflow replan <run_id> --reason "<short reason>"
   ```

   Honor the `max_replans` budget. If the CLI refuses because the budget is exhausted, stop and tell the user.
5. Produce a new plan that explicitly addresses the failure. Include the failure context in your own reasoning:
   - If a file was missing, don't assume its API exists.
   - If a type was wrong, fix the types first, then use them.
   - If a test was the failure, design the new plan to add the test last.
6. Save the new plan by piping it to `workflow plan-save --run <id> --plan -`.
7. Show the user: old step count vs new step count, and confirm before executing.
8. On confirmation, execute steps as in `workflow:task` step 5.
