from __future__ import annotations

import sys
from pathlib import Path

from workflow.state.config import load_config
from workflow.state.run import write_step_artifacts
from workflow.util.log import color, fail, info, ok
from workflow.validator.runner import run_validation


def run(*, cwd: Path, run_id: str | None, step_num: int | None) -> None:
    config = load_config(cwd)
    result = run_validation(cwd, config.get("validation") or {})

    for r in result["results"]:
        if r.get("skipped"):
            info(color.dim(f"skip {r['name']}"))
        elif r["ok"]:
            ok(f"{r['name']} ({r['command']})")
        else:
            fail(f"{r['name']} ({r['command']})")

    if run_id and step_num is not None:
        log_parts: list[str] = []
        for r in result["results"]:
            if r.get("skipped"):
                log_parts.append(f"# {r['name']}: skipped\n")
            else:
                status = "ok" if r["ok"] else "FAILED"
                log_parts.append(f"# {r['name']}: {status}\n{r['output']}\n")
        write_step_artifacts(cwd, run_id, step_num, validate_log="\n".join(log_parts))

    if not result["ok"]:
        failed = next(r for r in result["results"] if not r["ok"])
        sys.stderr.write(failed["output"])
        sys.exit(1)
