from __future__ import annotations

import json as _json
import sys
from pathlib import Path

from workflow.state.run import find_resumable_run, load_state, next_pending_step, run_exists
from workflow.util.log import fatal


def run(*, cwd: Path, run_id: str | None) -> None:
    if run_id:
        if not run_exists(cwd, run_id):
            fatal(f"Unknown run: {run_id}")
            return
        state = load_state(cwd, run_id)
    else:
        state = find_resumable_run(cwd)
        if state is None:
            fatal("No resumable run found.")
            return

    nxt = next_pending_step(state)
    payload = {
        "run_id": state["id"],
        "status": state["status"],
        "total_steps": len(state.get("steps") or []),
        "current_step": state.get("current_step"),
        "next_step": (
            {"num": nxt["num"], "title": nxt["title"], "files": nxt.get("files", [])}
            if nxt else None
        ),
        "last_error": state.get("last_error"),
    }
    sys.stdout.write(_json.dumps(payload, indent=2) + "\n")
