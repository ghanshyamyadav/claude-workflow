---
name: workflow:init
description: Index the repo, build the graph, detect test/lint commands.
---

You are running the **workflow:init** slash command.

Run the bootstrap step for this repo. This is a one-time per-repo setup.

Steps:

1. Run `workflow init` via Bash. It will:
   - detect stack (package.json, pyproject, Cargo, go.mod, etc.)
   - write `.workflow/config.json` with detected lint/typecheck/test commands
   - build the repo graph via the configured `graph_provider` (default: `graphify`, which shells out to the `graphify` CLI and writes `.workflow/graphify-out/`)
   - project `.workflow/graphify-out/GRAPH_REPORT.md` into `.workflow/repo_summary.md`
2. If the command fails with `graphify CLI not found on PATH`, tell the user to install it once with `uv tool install graphifyy` (or `pipx install graphifyy`) followed by `graphify install`, then re-run `/workflow:init`. Do not attempt the install yourself.
3. Read the resulting `.workflow/config.json` back and show the user the detected `validation` commands.
4. If any of `validation.lint`, `validation.typecheck`, or `validation.test` are `null` or look wrong, ask the user whether to edit them.
5. Tell the user:
   - What stack was detected.
   - The node/edge count graphify reported (or the file count, if the builtin provider was used).
   - That `.workflow/graphify-out/graph.json` and `GRAPH_REPORT.md` are safe to commit so teammates inherit the graph.
   - That they can now run `/workflow:task "<description>"`.

Do not run any other workflow commands here.
