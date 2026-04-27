from __future__ import annotations

import json
import sys
from pathlib import Path

from workflow.state.run import run_exists, save_plan
from workflow.util.fs import read_text
from workflow.util.log import fatal, ok


def run(*, cwd: Path, run_id: str, plan_path: str) -> None:
    if not run_exists(cwd, run_id):
        fatal(f"Unknown run: {run_id}")
        return

    if plan_path == "-":
        raw = sys.stdin.read()
    else:
        raw = read_text(Path(plan_path))

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as err:
        fatal(f"plan is not valid JSON: {err}")
        return

    steps = parsed.get("steps") if isinstance(parsed, dict) else None
    if not isinstance(steps, list) or not steps:
        fatal('plan must have a non-empty "steps" array')
        return

    for i, s in enumerate(steps):
        if not isinstance(s, dict) or not s.get("title"):
            fatal(f'step {i + 1} is missing "title"')
            return
        if not isinstance(s.get("files"), list):
            s["files"] = []

    save_plan(cwd, run_id, parsed)
    ok(f"Plan saved ({len(steps)} step{'' if len(steps) == 1 else 's'})")
