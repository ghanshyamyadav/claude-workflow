from __future__ import annotations

import re


_FENCED_DIFF = re.compile(r"```(?:diff|patch)\s*\n(.*?)\n```", re.DOTALL)
_ANY_FENCE = re.compile(r"```[^\n]*\n(.*?)\n```", re.DOTALL)
_LOOKS_LIKE_DIFF = re.compile(r"^(?:diff --git |--- [^\n]+\n\+\+\+ )", re.MULTILINE)


def extract_diff(output: str) -> str:
    """Extract a unified diff from the executor's raw output.

    Accepts a ```diff fenced block, a generic fenced block whose contents look
    like a diff, or a bare diff. Raises ValueError otherwise. When multiple
    fenced blocks are present, the first one whose contents look like a diff
    wins — so a leading prose/code example can't mask a real diff below.
    """
    if not output:
        raise ValueError("empty executor output")

    for m in _FENCED_DIFF.finditer(output):
        return _normalize(m.group(1))

    for m in _ANY_FENCE.finditer(output):
        if _looks_like_diff(m.group(1)):
            return _normalize(m.group(1))

    if _looks_like_diff(output):
        return _normalize(output)

    raise ValueError("executor output contains no unified diff")


def _looks_like_diff(s: str) -> bool:
    return bool(_LOOKS_LIKE_DIFF.search(s))


def _normalize(s: str) -> str:
    out = s.replace("\r\n", "\n").replace("\r", "\n")
    if not out.endswith("\n"):
        out += "\n"
    return out
