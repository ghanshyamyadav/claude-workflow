from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from workflow.graph.summarize import summarize_file
from workflow.state.paths import graph_dir, summary_path
from workflow.util.fs import ensure_dir, write_json, write_text


_IGNORE_DIRS = {
    "node_modules", ".git", ".svn", ".hg", ".idea", ".vscode", "dist", "build", "out",
    "coverage", ".next", ".nuxt", ".cache", ".turbo", "target", ".venv", "venv",
    "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".DS_Store",
    ".workflow", ".claude",
}

_CODE_EXT = {
    ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs",
    ".py", ".go", ".rs", ".rb", ".java", ".kt", ".swift",
    ".c", ".h", ".cc", ".cpp", ".hpp", ".m", ".mm",
    ".php", ".cs", ".scala", ".ex", ".exs", ".lua",
}


def build_graph(cwd: Path, *, full: bool = False) -> dict:
    all_files = _walk(cwd)
    code = [p for p in all_files if p.suffix.lower() in _CODE_EXT]

    entries: list[dict] = []
    for abs_path in code:
        rel = str(abs_path.relative_to(cwd))
        summary = summarize_file(abs_path, rel)
        if summary:
            entries.append(summary)

    d = graph_dir(cwd)
    ensure_dir(d)
    write_json(d / "index.json", {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "file_count": len(entries),
        "files": entries,
    })

    write_text(summary_path(cwd), _render_summary(cwd, entries))
    return {"files": len(entries), "all_files": len(all_files)}


def _walk(root: Path) -> list[Path]:
    out: list[Path] = []
    def recurse(d: Path) -> None:
        try:
            entries = list(d.iterdir())
        except (OSError, PermissionError):
            return
        for e in entries:
            if e.name in _IGNORE_DIRS:
                continue
            if e.is_symlink():
                continue
            if e.is_dir():
                recurse(e)
            elif e.is_file():
                out.append(e)
    recurse(root)
    return out


def _render_summary(cwd: Path, entries: list[dict]) -> str:
    from collections import defaultdict

    lines = [
        "# Repo summary",
        "",
        f"Root: `{cwd}`",
        f"Files indexed: {len(entries)}",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
    ]

    by_dir: dict[str, list[dict]] = defaultdict(list)
    for e in entries:
        parent = str(Path(e["path"]).parent)
        by_dir[parent].append(e)

    for d in sorted(by_dir):
        lines.append(f"## {'(root)' if d == '.' else d}")
        lines.append("")
        for e in sorted(by_dir[d], key=lambda x: x["path"]):
            name = Path(e["path"]).name
            syms = e.get("symbols") or []
            sym_part = f" — {', '.join(syms[:8])}" if syms else ""
            trunc = " (large, skipped)" if e.get("truncated") else ""
            binary = " (binary)" if e.get("binary") else ""
            lines.append(f"- `{name}`{sym_part}{trunc}{binary}")
        lines.append("")

    return "\n".join(lines)
