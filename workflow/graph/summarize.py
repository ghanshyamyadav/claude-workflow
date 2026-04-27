from __future__ import annotations

import re
from pathlib import Path


_IMPORT_PATTERNS = [
    re.compile(r"""^\s*import\s+.*?from\s+['"]([^'"]+)['"]"""),            # ES modules
    re.compile(r"""^\s*import\s+['"]([^'"]+)['"]"""),                       # ES side-effect
    re.compile(r"""^\s*from\s+(\S+)\s+import\b"""),                         # Python from
    re.compile(r"""^\s*import\s+(\S+)"""),                                  # Python import
    re.compile(r"""^\s*require\s*\(\s*['"]([^'"]+)['"]\s*\)"""),            # CJS require
]

_DECL_PATTERNS = [
    re.compile(r"^\s*export\s+(?:default\s+)?(?:async\s+)?(?:function|class|const|let|var|interface|type|enum)\s+([A-Za-z_$][\w$]*)"),
    re.compile(r"^\s*(?:async\s+)?function\s+([A-Za-z_$][\w$]*)"),
    re.compile(r"^\s*class\s+([A-Za-z_$][\w$]*)"),
    re.compile(r"^\s*def\s+([A-Za-z_]\w*)"),
    re.compile(r"^\s*class\s+([A-Za-z_]\w*)"),
]


def summarize_file(abs_path: Path, rel_path: str, *, max_bytes: int = 200_000) -> dict | None:
    try:
        stat = abs_path.stat()
    except OSError:
        return None
    if not abs_path.is_file():
        return None
    if stat.st_size > max_bytes:
        return {"path": rel_path, "bytes": stat.st_size, "truncated": True, "imports": [], "symbols": []}

    try:
        text = abs_path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return {"path": rel_path, "bytes": stat.st_size, "binary": True, "imports": [], "symbols": []}

    imports: list[str] = []
    symbols: list[str] = []
    seen_imports: set[str] = set()

    for line in text.splitlines()[:400]:
        for pat in _IMPORT_PATTERNS:
            m = pat.match(line)
            if m:
                name = m.group(1)
                if name and name not in seen_imports:
                    seen_imports.add(name)
                    imports.append(name)
                break
        for pat in _DECL_PATTERNS:
            m = pat.match(line)
            if m:
                name = m.group(1)
                if name not in symbols:
                    symbols.append(name)
                break
        if len(symbols) >= 40:
            break

    return {
        "path": rel_path,
        "bytes": stat.st_size,
        "lines": text.count("\n") + 1,
        "imports": imports[:30],
        "symbols": symbols[:30],
    }
