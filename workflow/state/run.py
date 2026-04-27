from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from workflow.state.paths import run_paths, runs_dir, step_paths
from workflow.util.fs import (
    ensure_dir,
    exists,
    list_dir,
    read_json,
    read_text,
    write_json,
    write_text,
)


# State schema (state.json):
#   id: str
#   description: str
#   status: one of 'planning' | 'in_progress' | 'needs_verify' | 'done' | 'failed' | 'interrupted'
#   current_step: int
#   steps: [{ num, title, status, attempts, files, last_error }]
#   replans: int
#   created_at, updated_at: ISO-8601 UTC
#   last_error: str | None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_run(cwd: Path, *, run_id: str, description: str, clarifications: list[dict] | None = None) -> dict:
    paths = run_paths(cwd, run_id)
    ensure_dir(paths.dir)
    ensure_dir(paths.steps)
    write_text(paths.task, _render_task_md(description, clarifications or []))

    state = {
        "id": run_id,
        "description": description,
        "status": "planning",
        "current_step": 0,
        "steps": [],
        "replans": 0,
        "created_at": _now(),
        "updated_at": _now(),
        "last_error": None,
    }
    write_json(paths.state, state)
    return state


def load_state(cwd: Path, run_id: str) -> dict:
    return read_json(run_paths(cwd, run_id).state)


def save_state(cwd: Path, state: dict) -> None:
    state["updated_at"] = _now()
    write_json(run_paths(cwd, state["id"]).state, state)


def run_exists(cwd: Path, run_id: str) -> bool:
    return exists(run_paths(cwd, run_id).state)


def save_plan(cwd: Path, run_id: str, plan: dict) -> dict:
    paths = run_paths(cwd, run_id)
    write_json(paths.plan, plan)
    state = load_state(cwd, run_id)
    state["steps"] = [
        {
            "num": i + 1,
            "title": s["title"],
            "status": "pending",
            "attempts": 0,
            "files": s.get("files", []),
            "last_error": None,
        }
        for i, s in enumerate(plan["steps"])
    ]
    state["status"] = "in_progress"
    state["current_step"] = 1
    save_state(cwd, state)
    return state


def load_plan(cwd: Path, run_id: str) -> dict | None:
    p = run_paths(cwd, run_id).plan
    if not exists(p):
        return None
    return read_json(p)


def list_runs(cwd: Path, *, limit: int = 10) -> list[dict]:
    d = runs_dir(cwd)
    out: list[dict] = []
    for name in list_dir(d):
        sp = d / name / "state.json"
        if not exists(sp):
            continue
        try:
            out.append(read_json(sp))
        except Exception:
            continue
    out.sort(key=lambda r: r.get("updated_at") or "", reverse=True)
    return out[:limit]


def find_current_run(cwd: Path) -> dict | None:
    runs = list_runs(cwd, limit=50)
    active = {"in_progress", "planning", "needs_verify"}
    for r in runs:
        if r.get("status") in active:
            return r
    for r in runs:
        if r.get("status") == "interrupted":
            return r
    return None


def find_resumable_run(cwd: Path) -> dict | None:
    resumable = {"in_progress", "interrupted", "planning"}
    for r in list_runs(cwd, limit=50):
        if r.get("status") in resumable:
            return r
    return None


def write_step_artifacts(
    cwd: Path,
    run_id: str,
    step_num: int,
    *,
    prompt: str | None = None,
    output: str | None = None,
    validate_log: str | None = None,
    patch: str | None = None,
) -> None:
    sp = step_paths(cwd, run_id, step_num)
    ensure_dir(sp.dir)
    if prompt is not None:
        write_text(sp.prompt, prompt)
    if output is not None:
        write_text(sp.output, output)
    if validate_log is not None:
        write_text(sp.validate, validate_log)
    if patch is not None:
        write_text(sp.patch, patch)


def read_step_artifacts(cwd: Path, run_id: str, step_num: int) -> dict[str, str | None]:
    sp = step_paths(cwd, run_id, step_num)

    def maybe(p: Path) -> str | None:
        return read_text(p) if exists(p) else None

    return {
        "prompt": maybe(sp.prompt),
        "output": maybe(sp.output),
        "validate_log": maybe(sp.validate),
        "patch": maybe(sp.patch),
    }


def next_pending_step(state: dict) -> dict | None:
    for s in state.get("steps", []):
        if s.get("status") in ("pending", "failed"):
            return s
    return None


def _render_task_md(description: str, clarifications: list[dict]) -> str:
    lines = ["# Task", "", description.strip(), ""]
    if clarifications:
        lines += ["## Clarifications", ""]
        for c in clarifications:
            lines.append(f"- **Q:** {c.get('q', '')}")
            lines.append(f"  **A:** {c.get('a', '')}")
        lines.append("")
    return "\n".join(lines)
