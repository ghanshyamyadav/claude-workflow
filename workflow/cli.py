from __future__ import annotations

import sys
from pathlib import Path

import click

from workflow import __version__
from workflow.commands import (
    exec_step as exec_step_cmd,
    init as init_cmd,
    install as install_cmd,
    plan_save as plan_save_cmd,
    refresh as refresh_cmd,
    replan as replan_cmd,
    resume as resume_cmd,
    status as status_cmd,
    task_new as task_new_cmd,
    validate as validate_cmd,
    verify as verify_cmd,
)
from workflow.util.log import fail


CWD_OPTION = click.option(
    "--cwd",
    type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
    default=lambda: Path.cwd(),
    show_default="current working directory",
    help="Target directory.",
)


@click.group(
    help="Plan, execute, and validate code changes via a repo graph + local-model subprocesses.",
    context_settings={"help_option_names": ["-h", "--help"]},
)
@click.version_option(__version__, prog_name="workflow")
def cli() -> None:
    pass


@cli.command("install", help="Drop slash commands into .claude/commands/ and seed .workflow/.")
@CWD_OPTION
@click.option("--force", is_flag=True, help="Overwrite existing slash command files.")
def install(cwd: Path, force: bool) -> None:
    install_cmd.run(cwd=cwd, force=force)


@cli.command("init", help="Scan the repo, detect tooling, and write .workflow/config.json + graph.")
@CWD_OPTION
def init(cwd: Path) -> None:
    init_cmd.run(cwd=cwd)


@cli.command("task-new", help="Create a new run directory and task.md. Prints the run_id on stdout.")
@CWD_OPTION
@click.option("--description", required=True, help="Task description.")
@click.option("--clarifications", default="[]", help="JSON array of {q, a} clarifying Q&A.")
@click.option(
    "--clarifications-file",
    default=None,
    help="Path to a file containing the clarifications JSON (use - for stdin). Overrides --clarifications.",
)
def task_new(cwd: Path, description: str, clarifications: str, clarifications_file: str | None) -> None:
    task_new_cmd.run(
        cwd=cwd,
        description=description,
        clarifications=clarifications,
        clarifications_file=clarifications_file,
    )


@cli.command("plan-save", help="Persist the planner output (plan.json) for a run.")
@CWD_OPTION
@click.option("--run", "run_id", required=True, help="Run id.")
@click.option("--plan", "plan_path", required=True, help="Path to plan.json (use - for stdin).")
def plan_save(cwd: Path, run_id: str, plan_path: str) -> None:
    plan_save_cmd.run(cwd=cwd, run_id=run_id, plan_path=plan_path)


@cli.command("exec-step", help="Execute a single step: spawn executor → apply patch → validate → retry.")
@CWD_OPTION
@click.option("--run", "run_id", required=True, help="Run id.")
@click.option("--step", "step_num", required=True, type=int, help="Step number (1-based).")
def exec_step(cwd: Path, run_id: str, step_num: int) -> None:
    exec_step_cmd.run(cwd=cwd, run_id=run_id, step_num=step_num)


@cli.command("validate", help="Run configured lint/typecheck/test commands. Exits non-zero on failure.")
@CWD_OPTION
@click.option("--run", "run_id", default=None, help="Run id (log output under the run).")
@click.option("--step", "step_num", default=None, type=int, help="Step number.")
def validate(cwd: Path, run_id: str | None, step_num: int | None) -> None:
    validate_cmd.run(cwd=cwd, run_id=run_id, step_num=step_num)


@cli.command("status", help="Print current and recent runs.")
@CWD_OPTION
@click.option("--json", "as_json", is_flag=True, help="Emit JSON.")
def status(cwd: Path, as_json: bool) -> None:
    status_cmd.run(cwd=cwd, as_json=as_json)


@cli.command("resume", help="Return the next pending step for the given (or most recent) run.")
@CWD_OPTION
@click.argument("run_id", required=False)
def resume(cwd: Path, run_id: str | None) -> None:
    resume_cmd.run(cwd=cwd, run_id=run_id)


@cli.command("replan", help="Mark a run for replanning; discards current plan and records reason.")
@CWD_OPTION
@click.option("--reason", default="", help="Why the plan is being discarded.")
@click.argument("run_id", required=False)
def replan(cwd: Path, run_id: str | None, reason: str) -> None:
    replan_cmd.run(cwd=cwd, run_id=run_id, reason=reason)


@cli.command("verify", help="Mark a run as needing a verifier pass (consumed by the verify slash command).")
@CWD_OPTION
@click.argument("run_id", required=False)
def verify(cwd: Path, run_id: str | None) -> None:
    verify_cmd.run(cwd=cwd, run_id=run_id)


@cli.command("refresh", help="Refresh the repo graph.")
@CWD_OPTION
@click.option("--full", is_flag=True, help="Full rebuild.")
def refresh(cwd: Path, full: bool) -> None:
    refresh_cmd.run(cwd=cwd, full=full)


def main() -> None:
    try:
        cli(standalone_mode=False)
    except click.exceptions.Abort:
        sys.exit(1)
    except click.exceptions.UsageError as err:
        err.show()
        sys.exit(err.exit_code or 2)
    except click.exceptions.ClickException as err:
        err.show()
        sys.exit(err.exit_code)
    except SystemExit:
        raise
    except Exception as err:  # top-level safety net
        fail(f"workflow: {err}")
        sys.exit(1)
