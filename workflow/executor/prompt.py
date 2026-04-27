from __future__ import annotations

import re


# Matches <think>…</think> and <thinking>…</thinking> blocks that some local
# models (Qwen3 family) emit when thinking mode is not fully suppressed.
_THINK_BLOCK_RE = re.compile(
    r"<think(?:ing)?>.*?</think(?:ing)?>", re.DOTALL | re.IGNORECASE
)

CLAUDE_CODE_SYSTEM_PROMPT = """/nothink

You are a code-editing subprocess inside a workflow runner.

CRITICAL: Your LAST output line MUST be exactly `DONE` or `NEEDS_REPLAN: <reason>`.
No text, no summary, no explanation after that line. Just the token on its own line.

You receive ONE step from a larger plan. Execute that step by editing files
directly with your tools. You have Read, Edit, and Write tools available.

Rules:

1. **Scope.** You may only modify files listed in the step's <files_in_scope>
   section. Reading files outside that list is allowed for context, but DO NOT
   edit, create, or delete any file outside the list. Out-of-scope edits are
   detected after you exit and reported back to the human. If you realize the
   step genuinely needs a file outside the list, stop and output
   `NEEDS_REPLAN: <reason>` instead of making the edit.

2. **Minimal diff.** Make the smallest change that satisfies the step. Do not
   refactor surrounding code, reformat unrelated lines, or rename variables
   that aren't part of the step.

3. **Termination — non-negotiable.**
   - If you completed the step: write `DONE` on the very last line and stop.
   - If the step is impossible as described: write `NEEDS_REPLAN: <short reason>` on the very last line and stop.
   - Do NOT write anything after `DONE` or `NEEDS_REPLAN:`.
   - Do NOT write both. Pick one.
   - If neither token appears, the runner marks the attempt failed and retries.

4. **No meta-commentary.** Do not describe what you did. Do not say "I have completed". Just end with DONE.

5. **No shell.** You have no Bash tool. Do not attempt to run commands.

6. **No thinking tags.** Do not emit <think>, </think>, <thinking>, or </thinking> tags in your output.
"""


def build_claude_code_prompt(
    *,
    task: str,
    step: dict,
    files_in_scope: list[str],
    retry_error: str | None = None,
) -> str:
    """Build the `-p` prompt for the Claude Code executor subprocess."""
    parts: list[str] = []

    # Remind local models of the termination contract right at the top.
    parts += [
        "REMINDER: your final output line MUST be exactly `DONE` or `NEEDS_REPLAN: <reason>` — nothing after it.",
        "",
    ]

    parts += ["<task>", task.strip(), "</task>", ""]

    parts += [f"<step num={step['num']!r} title={step['title']!r}>"]
    if step.get("description"):
        parts += [step["description"].strip()]
    if step.get("constraints"):
        parts.append("Constraints:")
        for c in step["constraints"]:
            parts.append(f"- {c}")
    parts += ["</step>", ""]

    parts += ["<files_in_scope>"]
    if files_in_scope:
        for f in files_in_scope:
            parts.append(f"- `{f}`")
    else:
        parts.append("(none — this step must not modify any file; if that is wrong, output `NEEDS_REPLAN`)")
    parts += ["</files_in_scope>", ""]

    parts += [
        "You may Read any file in the repo for context, but you may ONLY Edit or",
        "Write the files listed in <files_in_scope>. If you need to change anything",
        "else, output `NEEDS_REPLAN: <reason>` as the last line and stop.",
        "",
    ]

    if retry_error:
        parts += [
            "<previous_failure>",
            retry_error.strip()[:4000],
            "</previous_failure>",
            "",
            "Fix the issue. The current tree already contains your previous edits — re-read",
            "the scoped files before deciding what to change.",
            "",
        ]

    parts += [
        "Execute the step now.",
        "When finished, write `DONE` on its own line as your very last output.",
        "If impossible as described, write `NEEDS_REPLAN: <reason>` as your very last output.",
        "Do not write anything after that line.",
    ]
    return "\n".join(parts)


def parse_termination(output: str) -> dict:
    """Parse the subprocess output for the termination signal.

    Returns one of:
      {"kind": "done"}
      {"kind": "needs_replan", "reason": "<text>"}
      {"kind": "missing"}  — no valid terminator found

    Strips <think>/<thinking> blocks before parsing so that Qwen3-family
    models don't bury the terminator inside a thinking block.  Scans the
    last 5 non-empty lines so trailing prose from local models doesn't
    cause a spurious "missing" result.
    """
    cleaned = _THINK_BLOCK_RE.sub("", output or "")
    lines = [ln.rstrip() for ln in cleaned.splitlines() if ln.strip()]
    if not lines:
        return {"kind": "missing"}

    # Scan last 5 lines; local models sometimes append a trailing sentence.
    for candidate in reversed(lines[-5:]):
        candidate = candidate.strip()
        if candidate == "DONE":
            return {"kind": "done"}
        if candidate.startswith("NEEDS_REPLAN"):
            _, _, reason = candidate.partition(":")
            return {"kind": "needs_replan", "reason": reason.strip() or "(no reason given)"}
    return {"kind": "missing"}
