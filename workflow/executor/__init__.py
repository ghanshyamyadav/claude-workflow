from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from workflow.executor.claude_code import claude_code_execute


def execute(
    *,
    config: dict[str, Any],
    cwd: Path,
    prompt: str,
    system: str,
) -> str:
    exec_cfg = config["executor"]
    temperature = exec_cfg.get("temperature")
    num_ctx = exec_cfg.get("num_ctx")
    return claude_code_execute(
        cwd=cwd,
        prompt=prompt,
        system=system,
        allowed_tools=list(exec_cfg.get("allowed_tools", ["Read", "Edit", "Write"])),
        max_turns=int(exec_cfg.get("max_turns", 12)),
        model=os.environ.get("OLLAMA_MODEL") or exec_cfg.get("model", ""),
        timeout=float(exec_cfg.get("timeout_seconds", 600)),
        temperature=float(temperature) if temperature is not None else None,
        num_ctx=int(num_ctx) if num_ctx is not None else None,
    )
