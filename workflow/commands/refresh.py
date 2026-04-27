from __future__ import annotations

from pathlib import Path

from workflow.graph.provider import summarize
from workflow.graph.refresh import refresh_graph
from workflow.util.log import ok, step


def run(*, cwd: Path, full: bool) -> None:
    step("Rebuilding graph (full)..." if full else "Refreshing graph...")
    result = refresh_graph(cwd, full=full)
    ok(summarize(result))
