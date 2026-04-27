from __future__ import annotations

import json as _json
import sys
from pathlib import Path

from workflow.state.config import load_config
from workflow.state.paths import run_paths
from workflow.state.run import find_current_run, load_state, run_exists, save_state
from workflow.util.fs import exists
from workflow.util.log import fatal, info, ok


def run(*, cwd: Path, run_id: str | None, reason: str) -> None:
    config = load_config(cwd)

    if run_id:
        if not run_exists(cwd, run_id):
            fatal(f"Unknown run: {run_id}")
            return
        state = load_state(cwd, run_id)
    else:
        state = find_current_run(cwd)
        if state is None:
            fatal("No active run to replan.")
            return

    max_replans = config.get("max_replans", 2)
    if state.get("replans", 0) >= max_replans:
        fatal(f"Replan budget exhausted ({state.get('replans', 0)}/{max_replans}).")
        return

    paths = run_paths(cwd, state["id"])
    next_replan = state.get("replans", 0) + 1
    if exists(paths.plan):
        backup = paths.dir / f"plan.previous.{next_replan}.json"
        paths.plan.rename(backup)
        try:
            rel = backup.relative_to(cwd)
            info(f"Previous plan archived at {rel}")
        except ValueError:
            info(f"Previous plan archived at {backup}")

    state["replans"] = next_replan
    state["status"] = "planning"
    state["current_step"] = 0
    state["steps"] = []
    state["last_error"] = reason or state.get("last_error")
    save_state(cwd, state)

    ok(f"Run {state['id']} marked for replanning (attempt {next_replan}/{max_replans}).")
    if reason:
        info(f"Reason recorded: {reason}")

    sys.stdout.write(_json.dumps(
        {"run_id": state["id"], "replans": next_replan, "reason": reason},
        indent=2,
    ) + "\n")
