from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def ensure_dir(d: Path) -> None:
    d.mkdir(parents=True, exist_ok=True)


def write_json(p: Path, data: Any) -> None:
    ensure_dir(p.parent)
    p.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def read_json(p: Path) -> Any:
    return json.loads(p.read_text(encoding="utf-8"))


def write_text(p: Path, text: str) -> None:
    ensure_dir(p.parent)
    p.write_text(text, encoding="utf-8")


def read_text(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def exists(p: Path) -> bool:
    return p.exists()


def list_dir(d: Path) -> list[str]:
    if not d.exists():
        return []
    return sorted(entry.name for entry in d.iterdir())
