from __future__ import annotations

import re
from datetime import datetime, timezone


def slugify(s: str) -> str:
    s = str(s).lower()
    s = re.sub(r"[^a-z0-9\s-]", "", s)
    s = s.strip()
    s = re.sub(r"\s+", "-", s)
    s = re.sub(r"-+", "-", s)
    return s.strip("-")


def make_run_id(description: str, now: datetime | None = None) -> str:
    if now is None:
        now = datetime.now(timezone.utc)
    date = now.strftime("%Y-%m-%d")
    slug = slugify(description)[:40] or "task"
    return f"{date}-{slug}"
