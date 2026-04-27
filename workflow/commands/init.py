from __future__ import annotations

import socket
import subprocess
from pathlib import Path
from urllib.parse import urlparse

from workflow.graph.provider import build_graph, resolve_provider, summarize
from workflow.state.config import DEFAULT_CONFIG, config_exists, load_config, save_config
from workflow.state.paths import workflow_root
from workflow.util.fs import ensure_dir
from workflow.util.log import color, info, ok, step, warn
from workflow.validator.detect import detect_validation


def run(*, cwd: Path) -> None:
    ensure_dir(workflow_root(cwd))

    step("Scanning repo...")
    detected = detect_validation(cwd)
    stack = ", ".join(detected["stack"]) if detected["stack"] else "unknown"
    info(f"  detected: {color.cyan(stack)}")

    existing = load_config(cwd) if config_exists(cwd) else DEFAULT_CONFIG
    validation = existing.get("validation") or {}
    config = {
        **existing,
        "validation": {
            "lint":      validation.get("lint")      if validation.get("lint")      is not None else detected.get("lint"),
            "typecheck": validation.get("typecheck") if validation.get("typecheck") is not None else detected.get("typecheck"),
            "test":      validation.get("test")      if validation.get("test")      is not None else detected.get("test"),
        },
    }
    save_config(cwd, config)
    ok("Config written to .workflow/config.json")

    provider = resolve_provider(cwd)
    step(f"Building graph via {provider}...")
    result = build_graph(cwd, provider=provider)
    ok(summarize(result))

    _suggest_gitignore_entries(cwd, provider=provider)
    _warn_if_not_git_repo(cwd)
    _preflight_executor_endpoint(config)

    info("")
    info("Ready. Edit .workflow/config.json if the detected lint/test commands are wrong.")


def _preflight_executor_endpoint(config: dict) -> None:
    """Best-effort TCP probe of the local Ollama server."""
    if not _tcp_probe("http://localhost:11434", timeout=1.0):
        warn("Ollama not reachable at http://localhost:11434")
        info("  Start Ollama before running `/workflow:task`.")


def _tcp_probe(url: str, *, timeout: float) -> bool:
    parsed = urlparse(url)
    host = parsed.hostname
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    if not host:
        return True  # can't reason about it — don't false-alarm
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _warn_if_not_git_repo(cwd: Path) -> None:
    """The out-of-scope edit check uses `git diff`; without git it silently no-ops."""
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=str(cwd), capture_output=True, text=True, timeout=5,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        warn("git not available — step scope enforcement will be disabled")
        return
    if proc.returncode != 0:
        warn("not a git repo — step scope enforcement will be disabled")
        info("  run `git init` to enable out-of-scope edit detection")


def _suggest_gitignore_entries(cwd: Path, *, provider: str) -> None:
    """Append provider-specific ignore lines to .gitignore if it exists."""
    gi = cwd / ".gitignore"
    if not gi.exists():
        return
    wanted: list[str] = []
    if provider == "graphify":
        wanted.append(".workflow/graphify-out/cache/")
    if not wanted:
        return
    current = gi.read_text(encoding="utf-8")
    existing_lines = {ln.strip() for ln in current.splitlines()}
    to_add = [line for line in wanted if line not in existing_lines]
    if not to_add:
        return
    prefix = "" if current.endswith("\n") or not current else "\n"
    gi.write_text(current + prefix + "\n".join(to_add) + "\n", encoding="utf-8")
    for line in to_add:
        info(f"  added to .gitignore: {line}")
