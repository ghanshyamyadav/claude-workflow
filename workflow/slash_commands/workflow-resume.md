---
name: workflow:resume
description: Resume the most recent interrupted run, or a specific one.
---

You are running the **workflow:resume** slash command.

Inputs:
- `$ARGUMENTS` may contain a specific `run_id`.

## Procedure

1. Run `workflow resume [run_id]` via Bash. It prints JSON with:
   - `run_id`, `status`, `total_steps`, `current_step`, `next_step`, `last_error`.
2. If `status` is `failed` and `last_error` is present, show the user a short summary and ask whether they want to:
   - continue from `next_step` anyway (run `workflow exec-step`), or
   - replan (run `/workflow:replan`).
3. If `next_step` is non-null, resume execution by looping `workflow exec-step --run <id> --step <n>` starting from `next_step.num`, exactly like `workflow:task` step 5.
4. If `next_step` is null (all steps done), either mark for verify (`workflow verify <id>`) and run the verifier pass, or tell the user the run is finished.

Do not re-plan unless the user explicitly asks.
