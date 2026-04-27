---
name: workflow:verify
description: Force a verifier pass on a completed run.
---

You are running the **workflow:verify** slash command.

Inputs:
- `$ARGUMENTS` may contain a specific `run_id`. If absent, use the current run.

## Procedure

1. Identify the run. If not provided, read `workflow status` to find the most recent non-failed run.
2. Read `.workflow/runs/<id>/task.md` — this is the source of truth for intended scope.
3. Run `git diff` (or `git diff --staged` if the user already staged) to see the complete set of changes.
4. Compare the diff against the task description:
   - Does every change map to something in the task or its clarifications?
   - Any out-of-scope refactors or drive-by edits?
   - Were tests modified? If so, were assertions weakened (e.g. `toBe` → `toBeTruthy`, `strictEqual` → `ok`)? Were any tests skipped or deleted?
   - Any new dependencies added that weren't justified?
5. Report findings as a short bulleted summary: `✓ Scope matches`, plus any `⚠` warnings with file and line.
6. Run `workflow verify <run_id>` to mark the run state.
7. Remind the user that patches are not auto-committed.
