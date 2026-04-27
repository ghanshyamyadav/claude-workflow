from __future__ import annotations

from pathlib import Path

from workflow.util.fs import exists, read_json


def detect_validation(cwd: Path) -> dict:
    found: dict = {"lint": None, "typecheck": None, "test": None, "stack": []}

    pkg_path = cwd / "package.json"
    if exists(pkg_path):
        try:
            pkg = read_json(pkg_path)
        except Exception:
            pkg = {}
        scripts = pkg.get("scripts") or {}
        if scripts.get("lint"):
            found["lint"] = "npm run lint"
        if scripts.get("typecheck"):
            found["typecheck"] = "npm run typecheck"
        elif scripts.get("type-check"):
            found["typecheck"] = "npm run type-check"
        if scripts.get("test"):
            found["test"] = "npm test"

        deps = {**(pkg.get("dependencies") or {}), **(pkg.get("devDependencies") or {})}
        if "typescript" in deps: found["stack"].append("TypeScript")
        if "eslint" in deps:     found["stack"].append("ESLint")
        if "jest" in deps:       found["stack"].append("Jest")
        if "vitest" in deps:     found["stack"].append("Vitest")
        if "mocha" in deps:      found["stack"].append("Mocha")
        if "react" in deps:      found["stack"].append("React")
        if "next" in deps:       found["stack"].append("Next.js")

    if exists(cwd / "pyproject.toml") or exists(cwd / "requirements.txt"):
        found["stack"].append("Python")
        found["lint"] = found["lint"] or "ruff check ."
        found["typecheck"] = found["typecheck"] or "mypy ."
        found["test"] = found["test"] or "pytest"

    if exists(cwd / "Cargo.toml"):
        found["stack"].append("Rust")
        found["lint"] = found["lint"] or "cargo clippy -- -D warnings"
        found["typecheck"] = found["typecheck"] or "cargo check"
        found["test"] = found["test"] or "cargo test"

    if exists(cwd / "go.mod"):
        found["stack"].append("Go")
        found["lint"] = found["lint"] or "go vet ./..."
        found["typecheck"] = found["typecheck"] or "go build ./..."
        found["test"] = found["test"] or "go test ./..."

    return found
