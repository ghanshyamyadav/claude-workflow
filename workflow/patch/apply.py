from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path


def apply_patch(cwd: Path, diff: str) -> dict:
    """Apply a unified diff at cwd using `git apply`, falling back to `patch`.

    Returns {"ok": bool, "tool": str, "output": str}.
    """
    tmp = tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", suffix=".diff", delete=False
    )
    try:
        tmp.write(diff)
        tmp.flush()
        tmp.close()

        git = _run(cwd, ["git", "apply", "--whitespace=nowarn", tmp.name])
        if git["ok"]:
            return {"ok": True, "tool": "git", "output": git["output"]}

        patch = _run(cwd, ["patch", "-p1", "-i", tmp.name])
        if patch["ok"]:
            return {"ok": True, "tool": "patch", "output": patch["output"]}

        return {
            "ok": False,
            "tool": "git+patch",
            "output": f"{git['output']}\n{patch['output']}",
        }
    finally:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass


def _run(cwd: Path, argv: list[str]) -> dict:
    try:
        proc = subprocess.run(argv, cwd=str(cwd), capture_output=True, text=True)
    except FileNotFoundError as err:
        return {"ok": False, "exitCode": -1, "output": f"{err}\n"}
    return {
        "ok": proc.returncode == 0,
        "exitCode": proc.returncode,
        "output": (proc.stdout or "") + (proc.stderr or ""),
    }
