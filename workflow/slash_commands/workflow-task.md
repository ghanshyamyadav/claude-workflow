---
name: workflow:task
description: Plan and execute a task end-to-end using the workflow runner.
---

You are running the **workflow:task** slash command.

You act as the **planner** and **orchestrator**. The `workflow` CLI handles
execution, validation, and state. Per-step code edits happen in a subprocess
against a local model — **do not read full files yourself or write patches
yourself** unless the user explicitly asks.

Inputs:
- `$ARGUMENTS` contains the task description. It may end with `--no-clarify`.

## Procedure

### 1. Pre-flight

- If `.workflow/config.json` does not exist, tell the user to run `/workflow:init` and stop.
- Read `.workflow/config.json` and `.workflow/repo_summary.md`. The summary is your primary source of repo context for planning — prefer it over reading files directly.

### 2. Clarifying questions

Unless `--no-clarify` is present or the config has `ask_clarifying_questions: false`:

- If the task is ambiguous on any of (scope, acceptance criteria, data model, user-facing behavior), ask up to 3 focused questions.
- Tell the user they can answer inline or say "use defaults".
- If the user answers with defaults/nothing, record `{q, a: "(default)"}` entries.

If the description clearly specifies everything, skip this step.

### 3. Create the run

If there are no clarifications, call:

```
workflow task-new --description "<task>" --clarifications '[]'
```

and capture the `run_id` from stdout. Otherwise, pipe the clarifications JSON
in via stdin — this avoids shell-quoting issues when answers contain quotes,
and keeps the content out of world-readable `/tmp`:

```
printf '%s' '[{"q":"...","a":"..."}]' | \
  workflow task-new --description "<task>" --clarifications-file -
```

Capture the `run_id` printed on stdout.

### 4. Plan

Using the repo summary (and **only reading individual files if strictly necessary**), produce a plan as JSON:

```json
{
  "steps": [
    {
      "title": "short imperative title",
      "description": "what changes, where, and why — enough for a code-editing subprocess to act on with only these files in context",
      "files": ["relative/path/a.ts", "relative/path/b.ts"],
      "constraints": ["optional", "list"]
    }
  ]
}
```

Rules:
- Every step must list the exact files it will touch. Steps that share no files may later run in parallel.
- Keep each step mechanical and focused. If a step is vague, split it or expand the description.
- Final step should add or update tests when appropriate.

Save the plan via stdin (keeps the plan out of `/tmp`):

```
printf '%s' '<plan-json>' | workflow plan-save --run <run_id> --plan -
```

Show the user the plan (titles + files only). If the plan is non-obvious, ask for a go-ahead.

### 5. Execute

For each step from 1 to N, run:

```
workflow exec-step --run <run_id> --step <n>
```

The CLI spawns the executor subprocess, applies the patch, runs validation, and retries on failure up to `max_attempts_per_step` total tries (including the first). Stream its output to the user.

If a step exits non-zero after retries:
- Inspect `.workflow/runs/<run_id>/steps/step-<n>/validate.log` and `output.txt`.
- Decide: is the step salvageable with a tweak, or does the plan need to change?
- If the plan needs to change, run `/workflow:replan` logic: call `workflow replan <run_id> --reason "<short reason>"` and go back to step 4. Honor the `max_replans` budget.

### 6. Verify (conditional)

After all steps complete, run `workflow status` to check the run. If:
- any step retried, OR
- a step modified tests, OR
- the config has `always_verify: true`

then produce a verifier pass:
- Run `git diff` to see the full change set.
- Compare against the original task description in `.workflow/runs/<run_id>/task.md`.
- Report: scope match, anything suspicious (weakened assertions, disabled tests, out-of-scope edits), and any follow-ups.
- Call `workflow verify <run_id>` to mark the run state.

### 7. Finish

- Tell the user: steps completed, any retries, whether verification was performed, and remind them that patches are **not** auto-committed — they should review with `git diff` and commit themselves.
