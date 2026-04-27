from __future__ import annotations

from pathlib import Path

from workflow.state.config import DEFAULT_CONFIG, config_exists, load_config
from workflow.util.log import warn


def resolve_provider(cwd: Path, override: str | None = None) -> str:
    if override:
        return override
    if config_exists(cwd):
        cfg = load_config(cwd)
        return cfg.get("graph_provider") or DEFAULT_CONFIG["graph_provider"]
    return DEFAULT_CONFIG["graph_provider"]


def summarize(result: dict) -> str:
    """Human-readable one-line summary of a build result."""
    provider = result.get("provider", "builtin")
    if provider == "graphify":
        nodes, edges = result.get("nodes"), result.get("edges")
        if nodes is not None and edges is not None:
            return f"Graphify indexed {nodes} nodes, {edges} edges"
        return "Graphify graph built"
    count = result.get("files") or 0
    return f"Indexed {count} file{'' if count == 1 else 's'}"


def build_graph(cwd: Path, *, full: bool = False, provider: str | None = None) -> dict:
    """Dispatch to the configured graph provider.

    Known providers:
      - "graphify": shell out to the graphify CLI (default).
      - "builtin":  the in-repo walker + per-file summarizer (fallback).
    """
    p = resolve_provider(cwd, provider)
    if p == "graphify":
        from workflow.graph.providers.graphify import build_graph as _build
        return _build(cwd, full=full)
    if p == "builtin":
        from workflow.graph.builder import build_graph as _build
        result = _build(cwd, full=full)
        result.setdefault("provider", "builtin")
        return result

    warn(f"Unknown graph_provider '{p}'. Falling back to builtin.")
    from workflow.graph.builder import build_graph as _build
    result = _build(cwd, full=full)
    result.setdefault("provider", "builtin")
    return result
