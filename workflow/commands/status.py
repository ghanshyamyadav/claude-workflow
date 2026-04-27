from __future__ import annotations

import json as _json
import sys
from pathlib import Path

from workflow.state.run import find_current_run, list_runs
from workflow.util.log import color, info


def run(*, cwd: Path, as_json: bool) -> None:
    current = find_current_run(cwd)
    recent = list_runs(cwd, limit=10)

    if as_json:
        sys.stdout.write(_json.dumps({"current": current, "recent": recent}, indent=2) + "\n")
        return

    if current:
        info(f"Current run: {color.bold(current['id'])}")
        status_line = f"  Status: {_status_label(current['status'])}"
        if current.get("current_step"):
            status_line += f" (step {current['current_step']}/{len(current.get('steps') or [])})"
        info(status_line)
        cur = next((s for s in (current.get("steps") or []) if s["num"] == current.get("current_step")), None)
        if cur:
            info(f"  Step:   {cur['title']}")
            files = cur.get("files") or []
            if files:
                info(f"  Files:  {', '.join(files)}")
        info("")
    else:
        info("No active run.")
        info("")

    if not recent:
        return
    info("Recent runs:")
    for r in recent:
        mark = _mark_for(r.get("status"))
        step_count = len(r.get("steps") or [])
        tail = f"({step_count} step{'' if step_count == 1 else 's'})"
        info(f"  {mark} {r['id']:<40} {_status_label(r.get('status', '')):<14} {tail}")


def _mark_for(s: str) -> str:
    if s == "done":         return color.green("✓")
    if s == "failed":       return color.red("✗")
    if s == "needs_verify": return color.yellow("?")
    if s in ("in_progress", "planning"): return color.blue("·")
    return color.dim("-")


def _status_label(s: str) -> str:
    return s or ""
