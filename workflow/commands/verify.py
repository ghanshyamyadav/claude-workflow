from __future__ import annotations

import json as _json
import sys
from pathlib import Path

from workflow.state.run import find_current_run, load_state, run_exists, save_state
from workflow.util.log import fatal, ok


def run(*, cwd: Path, run_id: str | None) -> None:
    if run_id:
        if not run_exists(cwd, run_id):
            fatal(f"Unknown run: {run_id}")
            return
        state = load_state(cwd, run_id)
    else:
        state = find_current_run(cwd)
        if state is None:
            fatal("No run to verify.")
            return

    state["status"] = "needs_verify"
    save_state(cwd, state)
    ok(f"Run {state['id']} marked for verification.")
    sys.stdout.write(_json.dumps({"run_id": state["id"], "status": state["status"]}, indent=2) + "\n")
