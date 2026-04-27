from __future__ import annotations

import subprocess
from pathlib import Path


_DEFAULT_PHASE_TIMEOUT = 1800.0  # 30 minutes per phase


def run_validation(cwd: Path, validation: dict | None) -> dict:
    """Run lint → typecheck → test in order. Stops on first failure."""
    phases = ("lint", "typecheck", "test")
    results: list[dict] = []
    validation = validation or {}
    timeout = _resolve_timeout(validation.get("timeout_seconds", _DEFAULT_PHASE_TIMEOUT))

    for name in phases:
        command = validation.get(name)
        if not command:
            results.append({"name": name, "command": None, "ok": True, "skipped": True, "output": ""})
            continue
        res = _run_shell(cwd, command, timeout)
        results.append({"name": name, "command": command, "skipped": False, **res})
        if not res["ok"]:
            return {"ok": False, "results": results}

    return {"ok": True, "results": results}


def _resolve_timeout(value: object) -> float | None:
    if value is None:
        return None
    try:
        t = float(value)
    except (TypeError, ValueError):
        return _DEFAULT_PHASE_TIMEOUT
    return t if t > 0 else None


def _run_shell(cwd: Path, command: str, timeout: float | None) -> dict:
    try:
        proc = subprocess.run(
            command,
            cwd=str(cwd),
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as err:
        partial = (err.stdout or "") + (err.stderr or "")
        if isinstance(partial, bytes):
            partial = partial.decode("utf-8", errors="replace")
        return {
            "ok": False,
            "exitCode": -1,
            "output": f"{partial}\n[timed out after {timeout}s]\n",
        }
    except OSError as err:
        return {"ok": False, "exitCode": -1, "output": f"{err}\n"}
    return {
        "ok": proc.returncode == 0,
        "exitCode": proc.returncode,
        "output": (proc.stdout or "") + (proc.stderr or ""),
    }
