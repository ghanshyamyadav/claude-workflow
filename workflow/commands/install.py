from __future__ import annotations

import shutil
from importlib import resources
from pathlib import Path

from workflow.state.paths import claude_commands_dir, workflow_root
from workflow.util.fs import ensure_dir, exists
from workflow.util.log import info, ok, warn


# Claude Code derives a command's invocation from its path under
# `.claude/commands/`. A file at `commands/workflow/init.md` is invoked as
# `/workflow:init`; a file at `commands/workflow-init.md` is `/workflow-init`.
# We want the colon-namespaced form, so install into a `workflow/` subdir and
# strip the `workflow-` prefix from filenames.
_SUBDIR = "workflow"
_FILENAME_PREFIX = "workflow-"


def run(*, cwd: Path, force: bool) -> None:
    dest = claude_commands_dir(cwd) / _SUBDIR
    ensure_dir(dest)
    ensure_dir(workflow_root(cwd))

    pkg = resources.files("workflow").joinpath("slash_commands")
    copied = 0
    skipped = 0

    for entry in pkg.iterdir():
        if not entry.name.endswith(".md"):
            continue
        short = entry.name.removeprefix(_FILENAME_PREFIX)
        target = dest / short
        if exists(target) and not force:
            warn(f"skip (exists): .claude/commands/{_SUBDIR}/{short}")
            skipped += 1
            continue
        with resources.as_file(entry) as src:
            shutil.copyfile(src, target)
        copied += 1

    ok(f"Installed {copied} slash command{'' if copied == 1 else 's'} to .claude/commands/{_SUBDIR}/")
    if skipped:
        info(f"  ({skipped} skipped — use --force to overwrite)")
    info("Next: run the '/workflow:init' slash command inside a Claude Code session.")
