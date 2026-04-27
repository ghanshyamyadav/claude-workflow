from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


def workflow_root(cwd: Path) -> Path:
    return cwd / ".workflow"


def config_path(cwd: Path) -> Path:
    return workflow_root(cwd) / "config.json"


def graph_dir(cwd: Path) -> Path:
    return workflow_root(cwd) / "graph"


def summary_path(cwd: Path) -> Path:
    return workflow_root(cwd) / "repo_summary.md"


def runs_dir(cwd: Path) -> Path:
    return workflow_root(cwd) / "runs"


def run_dir(cwd: Path, run_id: str) -> Path:
    return runs_dir(cwd) / run_id


def claude_commands_dir(cwd: Path) -> Path:
    return cwd / ".claude" / "commands"


@dataclass(frozen=True)
class RunPaths:
    dir: Path
    task: Path
    plan: Path
    state: Path
    steps: Path


def run_paths(cwd: Path, run_id: str) -> RunPaths:
    d = run_dir(cwd, run_id)
    return RunPaths(
        dir=d,
        task=d / "task.md",
        plan=d / "plan.json",
        state=d / "state.json",
        steps=d / "steps",
    )


@dataclass(frozen=True)
class StepPaths:
    dir: Path
    prompt: Path
    output: Path
    validate: Path
    patch: Path


def step_paths(cwd: Path, run_id: str, step_num: int) -> StepPaths:
    d = run_dir(cwd, run_id) / "steps" / f"step-{step_num}"
    return StepPaths(
        dir=d,
        prompt=d / "prompt.txt",
        output=d / "output.txt",
        validate=d / "validate.log",
        patch=d / "patch.diff",
    )
