from __future__ import annotations

import subprocess
from pathlib import Path

from workflow.executor import execute
from workflow.executor.prompt import (
    CLAUDE_CODE_SYSTEM_PROMPT,
    build_claude_code_prompt,
    parse_termination,
)
from workflow.state.config import load_config
from workflow.state.paths import run_paths
from workflow.state.run import (
    load_plan,
    load_state,
    run_exists,
    save_state,
    write_step_artifacts,
)
from workflow.util.fs import exists, read_text
from workflow.util.log import color, fail, fatal, info, ok, step, warn
from workflow.validator.runner import run_validation


def run(*, cwd: Path, run_id: str, step_num: int) -> None:
    if not run_exists(cwd, run_id):
        fatal(f"Unknown run: {run_id}")
        return

    config = load_config(cwd)
    plan = load_plan(cwd, run_id)
    if plan is None:
        fatal(f"No plan.json for run {run_id}. Save a plan first.")
        return

    steps = plan["steps"]
    if step_num < 1 or step_num > len(steps):
        fatal(f"Step {step_num} out of range (plan has {len(steps)} steps).")
        return

    plan_step = steps[step_num - 1]
    state = load_state(cwd, run_id)
    state_step = next((s for s in state["steps"] if s["num"] == step_num), None)
    if state_step is None:
        fatal(f"Step {step_num} not found in state.")
        return

    task = read_text(run_paths(cwd, run_id).task)
    max_attempts = _max_attempts(config)
    in_scope = list(plan_step.get("files") or [])
    retry_error: str | None = None
    attempt = 0

    _warn_if_git_unavailable(cwd)

    exec_cfg = config["executor"]
    model = exec_cfg.get("model", "")

    while True:
        attempt += 1
        state_step["attempts"] = attempt
        state["current_step"] = step_num
        state["status"] = "in_progress"
        save_state(cwd, state)

        step(f"[step {step_num}/{len(plan['steps'])}] {plan_step['title']}")
        label = f"ollama launch claude ({model})" if model else "ollama launch claude"
        info(f"  spawning executor ({color.dim(label)})...")

        prompt = build_claude_code_prompt(
            task=task,
            step={"num": step_num, **plan_step},
            files_in_scope=in_scope,
            retry_error=retry_error,
        )

        pre_changed = _list_changed_files(cwd)

        try:
            raw_output = execute(config=config, cwd=cwd, prompt=prompt, system=CLAUDE_CODE_SYSTEM_PROMPT)
        except Exception as err:
            retry_error = f"executor error: {err}"
            fail(f"  executor failed: {err}")
            write_step_artifacts(cwd, run_id, step_num, prompt=prompt, output=str(err))
            if attempt >= max_attempts:
                _record_failure(cwd, state, state_step, retry_error)
                return
            continue

        write_step_artifacts(cwd, run_id, step_num, prompt=prompt, output=raw_output)

        term = parse_termination(raw_output)
        if term["kind"] == "needs_replan":
            reason = term.get("reason", "")
            fail(f"  subprocess requested replan: {reason}")
            state_step["status"] = "failed"
            state_step["last_error"] = f"NEEDS_REPLAN: {reason}"
            state["status"] = "failed"
            state["last_error"] = f"step {step_num}: NEEDS_REPLAN: {reason}"
            save_state(cwd, state)
            return

        if term["kind"] == "missing":
            retry_error = "subprocess did not end with `DONE` or `NEEDS_REPLAN:` — cannot confirm completion"
            fail(f"  {retry_error}")
            if attempt >= max_attempts:
                _record_failure(cwd, state, state_step, retry_error)
                return
            continue

        post_changed = _list_changed_files(cwd)
        out_of_scope = _diff_out_of_scope(pre_changed, post_changed, in_scope)
        if out_of_scope:
            warn(f"  edited outside scope: {', '.join(out_of_scope)}")

        info("  validating...")
        validation = run_validation(cwd, config.get("validation") or {})
        write_step_artifacts(cwd, run_id, step_num, validate_log=_render_log(validation))

        if validation["ok"]:
            for r in validation["results"]:
                name = r["name"]
                if r.get("skipped"):
                    info(f"    {color.dim(f'skip {name}')}")
                else:
                    info(f"    {color.green('✓')} {name}")
            state_step["status"] = "done"
            state_step["last_error"] = None
            if out_of_scope:
                state_step["out_of_scope_edits"] = out_of_scope
            _advance(state)
            save_state(cwd, state)
            return

        failed = next(r for r in validation["results"] if not r["ok"])
        retry_error = f"{failed['name']} failed ({failed['command']}):\n{failed['output']}"
        fail(f"  {failed['name']} failed")
        if attempt >= max_attempts:
            _record_failure(cwd, state, state_step, retry_error)
            return
        info("  retrying with error context...")


_GIT_WARNING_EMITTED = False


def _warn_if_git_unavailable(cwd: Path) -> None:
    global _GIT_WARNING_EMITTED
    if _GIT_WARNING_EMITTED:
        return
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=str(cwd), capture_output=True, text=True, timeout=5,
        )
        available = proc.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        available = False
    if not available:
        warn("git unavailable — out-of-scope edit detection is disabled for this run")
    _GIT_WARNING_EMITTED = True


def _list_changed_files(cwd: Path) -> set[str]:
    try:
        tracked = subprocess.run(
            ["git", "diff", "--name-only", "HEAD"],
            cwd=str(cwd), capture_output=True, text=True, timeout=10,
        )
        if tracked.returncode != 0:
            return set()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return set()

    out = {line.strip() for line in tracked.stdout.splitlines() if line.strip()}
    try:
        untracked = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard"],
            cwd=str(cwd), capture_output=True, text=True, timeout=10,
        )
        if untracked.returncode == 0:
            out |= {line.strip() for line in untracked.stdout.splitlines() if line.strip()}
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return out


def _diff_out_of_scope(pre: set[str], post: set[str], in_scope: list[str]) -> list[str]:
    return sorted((post - pre) - set(in_scope))


def _max_attempts(config: dict) -> int:
    raw = config.get("max_attempts_per_step")
    if raw is None:
        return 3
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return 3
    return max(1, value)


def _advance(state: dict) -> None:
    nxt = next((s for s in state["steps"] if s["status"] == "pending"), None)
    if nxt is not None:
        state["current_step"] = nxt["num"]
        state["status"] = "in_progress"
    else:
        any_failed = any(s["status"] == "failed" for s in state["steps"])
        state["status"] = "failed" if any_failed else "needs_verify"


def _record_failure(cwd: Path, state: dict, state_step: dict, err: str) -> None:
    state_step["status"] = "failed"
    state_step["last_error"] = err
    state["last_error"] = err
    state["status"] = "failed"
    save_state(cwd, state)
    fatal(f"Step {state_step['num']} failed after max retries.")


def _render_log(validation: dict) -> str:
    parts: list[str] = []
    for r in validation["results"]:
        if r.get("skipped"):
            parts.append(f"# {r['name']}: skipped (not configured)\n")
        else:
            status_label = "ok" if r["ok"] else "FAILED"
            parts.append(f"# {r['name']}: {status_label} ({r['command']})\n{r['output']}\n")
    return "\n".join(parts)
