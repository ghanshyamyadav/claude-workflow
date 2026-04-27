from __future__ import annotations

from pathlib import Path

from workflow.graph.provider import build_graph


def refresh_graph(cwd: Path, *, full: bool = False) -> dict:
    # The graphify provider is incremental by default (re-extracts only
    # changed files via its SHA256 cache); --full clears that cache.
    # The builtin provider always rebuilds from scratch regardless of `full`.
    return build_graph(cwd, full=full)
