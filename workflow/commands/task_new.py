from __future__ import annotations

import json
import sys
from pathlib import Path

from workflow.state.run import create_run, run_exists
from workflow.util.fs import read_text
from workflow.util.log import fatal
from workflow.util.run_id import make_run_id


def run(
    *,
    cwd: Path,
    description: str,
    clarifications: str,
    clarifications_file: str | None = None,
) -> None:
    raw = _read_clarifications(clarifications, clarifications_file)

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        fatal("clarifications must be valid JSON")
        return  # unreachable — fatal raises
    if not isinstance(parsed, list):
        fatal("clarifications must be a JSON array")
        return

    run_id = make_run_id(description)
    n = 2
    while run_exists(cwd, run_id):
        run_id = f"{make_run_id(description)}-{n}"
        n += 1

    create_run(cwd, run_id=run_id, description=description, clarifications=parsed)
    sys.stdout.write(f"{run_id}\n")


def _read_clarifications(inline: str, from_file: str | None) -> str:
    """Resolve the clarifications JSON source.

    --clarifications-file wins when provided ("-" means stdin). Otherwise the
    inline --clarifications string is used. The file path lets the caller avoid
    quoting a JSON blob on the shell, where embedded quotes break things.
    """
    if from_file is None:
        return inline
    if from_file == "-":
        return sys.stdin.read()
    return read_text(Path(from_file))
