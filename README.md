# workflow

A set of Claude Code slash commands that turn natural-language tasks into validated code changes — using a repo graph for context, a strong model to plan, and your existing tools (lint, typecheck, tests) to validate.

> Status: early. Expect breaking changes.

## Why

When you ask Claude Code to make a change, it reads files on demand — which is fine for small tasks but gets expensive and error-prone in larger repos. `workflow` adds two things:

1. A persistent graph of your repo — built by [graphify](https://github.com/safishamsi/graphify) using Tree-sitter to extract code structure, with a human-readable summary projected into `.workflow/repo_summary.md` — so planning happens against summaries and structure, not full files.
2. An offloaded execution layer: once Claude plans the task, each step runs in a **separate subprocess against a local model**, not in your Claude Code session. Your main session keeps the plan in context and orchestrates; the cheap work happens elsewhere.

The result: Claude Code stays focused on planning and orchestration, and per-step edits don't chew through your context window or your API budget.

## How it works

```
/workflow:task
   └─> clarify (if needed)
   └─> plan                          [Claude Code session]
   └─> spawn subprocess per step     [local model, e.g. Ollama]
         └─> edit files → patch
         └─> validate (lint/typecheck/test)
         └─> retry on failure
   └─> verify (conditional)          [Claude Code session]
   └─> sync graph → done
```

- **Plan** (Claude Code session): Claude reads the graph + summaries and produces an ordered list of steps with file targets. Asks clarifying questions if the task is ambiguous.
- **Execute** (subprocess, local model): for each step, `workflow` spawns a subprocess running your configured local model (Ollama by default). The subprocess gets only the step definition and the files named in it — nothing else. It produces a patch and exits.
- **Validate** (subprocess): runs your lint / typecheck / test commands. On failure, the step retries with the error in context. All of this happens outside the Claude Code session.
- **Verify** (conditional, Claude Code session): Claude reviews the full diff if a step retried, scope expanded, or tests were modified.
- **Sync**: graph updates after the task so the next one starts fresh.

### Why subprocesses?

- **Context isolation.** Each step starts clean. A bad edit in step 2 can't pollute the context of step 3.
- **Parallelism later.** Independent steps can fan out to multiple subprocesses once the graph proves their file sets don't overlap (roadmap).
- **Your Claude Code session stays light.** Only plans, diffs, and summaries flow back — never full file contents.
- **Local models are actually cheap here.** A 14B model running locally is plenty for mechanical edits when the step is well-specified.

## Install

> `workflow-cli` is not yet on PyPI. Install from source while we're pre-1.0:

```bash
pipx install git+https://github.com/ghanshyamyadav/claude-workflow
workflow install
```

Or, to test against a local clone:

```bash
git clone https://github.com/ghanshyamyadav/claude-workflow && cd claude-workflow
pipx install -e .
workflow install --cwd /path/to/your/repo
```

This drops the slash commands into `.claude/commands/workflow/` (so Claude Code invokes them as `/workflow:init`, `/workflow:task`, …) and creates `.workflow/` in your target repo. Commit both so the rest of your team inherits them.

### Graphify

The default graph provider shells out to the [graphify](https://github.com/safishamsi/graphify) CLI. Install it once per machine:

```bash
uv tool install graphifyy   # or: pipx install graphifyy
graphify install            # registers the skill under ~/.claude/skills/graphify
```

> Not a typo — the PyPI package is `graphifyy` (two y's); the binary it installs is `graphify` (one y).

`workflow init` and `workflow refresh` call `graphify update <repo>` under the hood. Graphify writes its artifacts to `.workflow/graphify-out/` — `graph.json` (queryable), `graph.html` (visualization), and `GRAPH_REPORT.md` (communities, god nodes, suggested questions). The report is projected into `.workflow/repo_summary.md` for the planner. `workflow init` appends `.workflow/graphify-out/cache/` to your `.gitignore` so the cache doesn't get committed. To fall back to the in-repo walker instead, set `"graph_provider": "builtin"` in `.workflow/config.json`.

## Usage

Open a Claude Code session in your repo and run:

```
/workflow:init
```

Then use the other commands as needed. Full reference below.

## Commands

All commands run inside a Claude Code session.

| Command | Description |
|---|---|
| `/workflow:init` | Index the repo, build the graph, detect test/lint commands. Run once per repo. |
| `/workflow:task "<description>"` | Plan and execute a task. May ask clarifying questions before planning. |
| `/workflow:status` | Show the current run (if any) and recent runs. |
| `/workflow:resume [<run_id>]` | Resume the most recent interrupted run, or a specific one. |
| `/workflow:replan [<run_id>]` | Throw out the current plan and start over with lessons learned. |
| `/workflow:verify [<run_id>]` | Force a verifier pass on a completed run. |
| `/workflow:refresh` | Rebuild or incrementally update the graph after big merges or manual edits. |

### `/workflow:init`

```
> /workflow:init

› Scanning repo...
  detected: TypeScript, Jest, ESLint
✓ Config written to .workflow/config.json
› Building graph via graphify...
✓ Graphify indexed 1284 nodes, 3106 edges

Ready. Edit .workflow/config.json if the detected lint/test commands are wrong.
```

Run once per repo. Commits the graph so teammates don't re-index.

### `/workflow:task "<description>"`

```
> /workflow:task "add rate limiting to /auth/login"
```

**Clarifying questions.** If the task is ambiguous, Claude pauses and asks before writing a plan:

```
I have a few questions before planning:

  1. What limit? (e.g. 10 requests / minute per IP)
  2. Where should limits be stored — in-memory, Redis, or something else?
  3. What response should rate-limited requests get? (429 with Retry-After?)

Answer inline, or say "use defaults" to skip.
```

Answers are saved to `runs/<run_id>/task.md` so the plan is reproducible.

**Provide answers upfront** to skip questions Claude can already answer:

```
> /workflow:task "add rate limiting to /auth/login: 10 req/min per IP, in-memory, 429 response"
```

**Skip clarifications entirely:**

```
> /workflow:task "add rate limiting to /auth/login" --no-clarify
```

**What you see during execution.** After planning, Claude spawns one subprocess per step. You see live status from each; edits happen out-of-context:

```
Plan ready: 4 steps.

[step 1/4] Create RateLimiter class
  spawning executor (claude-code @ http://localhost:4000 (qwen2.5-coder:14b))...
  validating... ✓ lint ✓ typecheck ✓ tests

[step 2/4] Register middleware
  spawning executor... ✓
  validating... ✓ lint ✓ typecheck ✓ tests

[step 3/4] Apply to /auth/login route
  spawning executor... ✓
  validating... ✗ typecheck failed: request.client.host is Optional
  retrying with error context... ✓
  validating... ✓ lint ✓ typecheck ✓ tests

[step 4/4] Add test
  spawning executor... ✓
  validating... ✓ lint ✓ typecheck ✓ tests

All steps done. Verifying (1 retry triggered review)...
✓ Scope matches task.
```

(With a raw-diff provider like `ollama`, the line reads `spawning executor (ollama/qwen2.5-coder:14b)… ✓ patch applied` instead.)

### `/workflow:status`

```
> /workflow:status

Current run: 2026-04-20-auth-rate-limit
  Status: in_progress (step 3/4)
  Step:   Apply RateLimiter to /auth/login route
  Files:  routes/auth.ts

Recent runs:
  ✓ 2026-04-19-fix-login-redirect      done    (2 steps)
  ✗ 2026-04-19-refactor-session-store  failed  (replan budget exhausted)
  ✓ 2026-04-18-add-logout-endpoint     done    (3 steps)
```

### `/workflow:resume`

```
> /workflow:resume
```

Picks up the most recent interrupted run from where it left off. Pass a run ID to resume a specific one:

```
> /workflow:resume 2026-04-20-auth-rate-limit
```

### `/workflow:replan`

When the current plan is wrong but the task is still what you want:

```
> /workflow:replan

Current plan has 2 failed steps. Replanning from scratch...
New plan has 5 steps (was 4). Continue? [y/N]
```

The new plan receives the history of the previous one and why it failed. Capped at `max_replans` (default 2).

### `/workflow:verify`

Force a verifier pass on any completed run — useful before committing:

```
> /workflow:verify 2026-04-20-auth-rate-limit

Reviewing diff against original task...
✓ Scope matches task description.
⚠ tests/auth.test.ts: assertion was weakened (toBe → toBeTruthy). Intentional?
```

### `/workflow:refresh`

```
> /workflow:refresh           # incremental
> /workflow:refresh --full    # full rebuild
```

Run after git merges, rebases, or manual edits made outside of `workflow`.

## Configuration

`.workflow/config.json`:

```json
{
  "planner_model": "claude-opus-4-7",
  "verifier_model": "claude-opus-4-7",
  "graph_provider": "graphify",
  "executor": {
    "provider": "claude-code",
    "model": "qwen3-coder:latest",
    "endpoint": "http://localhost:11434",
    "timeout_seconds": 600,
    "max_parallel": 1,
    "claude_binary": "claude",
    "max_turns": 12,
    "allowed_tools": ["Read", "Edit", "Write"],
    "temperature": 0.1,
    "num_ctx": 65536,
    "shim_endpoint": "http://localhost:4000",
    "shim_api_key": "",
    "shim_model": ""
  },
  "ask_clarifying_questions": true,
  "always_verify": false,
  "validation": {
    "lint": "npm run lint",
    "typecheck": "npm run typecheck",
    "test": "npm test",
    "timeout_seconds": 1800
  },
  "max_attempts_per_step": 4,
  "max_replans": 2
}
```

`planner_model`, `verifier_model`, `graph_provider`, and `executor.max_parallel`
are metadata read by the Claude Code slash commands (planner, verifier,
orchestrator). The Python CLI itself ignores them.

`validation.timeout_seconds` caps each phase (lint, typecheck, test) individually.
Set it to `null` to disable the timeout. `max_attempts_per_step` counts the first
try plus any retries.

**Executor providers supported:**

- `claude-code` *(default)* — spawns the `claude` CLI as each step's subprocess, backed by a local model via an Anthropic-compatible shim. Richer than raw diffs: the subprocess reads files, self-corrects, and edits in place via Claude Code's own tools.
- `ollama` — raw-diff executor. Calls Ollama directly, expects a unified-diff response, and applies it with `git apply`.
- `llamacpp` — raw-diff executor against llama.cpp's OpenAI-compatible server.
- `openai-compatible` — raw-diff executor for any OpenAI-compatible endpoint (LM Studio, vLLM, Together, etc.).

### Running the Anthropic-compatible shim

The `claude-code` provider points Claude Code at a local proxy that exposes an Anthropic-style API backed by your local model. [LiteLLM](https://docs.litellm.ai/) is the simplest option:

```bash
pip install 'litellm[proxy]'
litellm --model ollama/qwen2.5-coder:14b --port 4000
```

Then ensure:
- `executor.shim_endpoint` (or `ANTHROPIC_BASE_URL`) points at the proxy.
- `claude` is installed and on PATH.

### Environment variables

A reference `.env.example` ships with the repo listing the env vars each provider honors. `workflow` does not auto-load `.env` — copy it to `.env` in your shell's rc file or `source .env` / `set -a; source .env; set +a` before running Claude Code. When set, env vars take precedence over the equivalent fields in `.workflow/config.json`.

| Variable | Purpose |
|---|---|
| `ANTHROPIC_BASE_URL` | Shim endpoint for the `claude-code` provider |
| `ANTHROPIC_API_KEY` | API key forwarded to the shim (any non-empty string works for local) |
| `OLLAMA_ENDPOINT` | Ollama base URL for raw-diff providers |
| `LLAMACPP_ENDPOINT` | llama.cpp base URL for raw-diff providers |
| `OPENAI_COMPATIBLE_ENDPOINT` | Base URL for any OpenAI-compatible raw-diff provider |
| `OPENAI_COMPATIBLE_API_KEY` | API key for the above |
| `WORKFLOW_EXECUTOR_MODEL` | Override the executor model without editing `config.json` |
| `OLLAMA_CONTEXT_LENGTH` | **Recommended.** Forces Ollama's context window regardless of `num_ctx`. Ollama silently clamps `num_ctx` in some versions ([#10974](https://github.com/ollama/ollama/issues/10974)); this env var is the reliable fix. Set to `65536` — Claude Code's system prompt alone is ~16K tokens. Add to your shell profile: `export OLLAMA_CONTEXT_LENGTH=65536` |

### Scope constraints on the subprocess

When using the `claude-code` provider, each step subprocess is launched with:

- `--allowedTools "Read Edit Write"` (configurable) — no Bash, no network.
- `--max-turns 12` (configurable) — hard cap on tool-loop iterations.
- A scoped prompt: "You may only modify files in this list. If you need to change anything else, stop and output `NEEDS_REPLAN: <reason>`."
- Required termination signal: the subprocess must end its output with `DONE` or `NEEDS_REPLAN: <reason>`. Anything else is treated as a failed attempt and retried.
- Post-hoc check: `git diff --name-only HEAD` after the subprocess exits. Files modified outside the scoped list are recorded on the run state as `out_of_scope_edits` and surfaced to you as a warning — this is detection, not prevention. A local model that ignores the scope rules can still write wherever the filesystem permits; treat the warning as a signal to review the diff before committing. Requires a git repo; without git the check silently no-ops (you'll see a one-time warning).

`max_parallel` controls how many step subprocesses can run at once. Default is 1 (sequential). Increase only after you trust your planner to correctly mark independent steps.

## What gets created

```
.claude/
└── commands/
    └── workflow/           # invoked as /workflow:init, /workflow:task, ...
        ├── init.md
        ├── task.md
        └── ...

.workflow/
├── config.json
├── repo_summary.md    # projected from .workflow/graphify-out/GRAPH_REPORT.md
├── graph/             # reserved for provider metadata
└── runs/
    └── <run_id>/
        ├── task.md             # original task + clarifying Q&A
        ├── plan.json
        ├── state.json
        └── steps/
            └── step-N/
                ├── prompt.txt    # what the subprocess received
                ├── output.txt    # what it returned
                ├── patch.diff    # raw-diff providers only
                └── validate.log
```

Patches are **not** auto-committed. Review with `git diff` before committing.

The graphify provider writes `graph.json`, `graph.html`, `GRAPH_REPORT.md`, and `cache/` under `.workflow/graphify-out/`. Commit `graph.json` and `GRAPH_REPORT.md` so teammates inherit the same graph; `cache/` can stay local.

## Requirements

- Claude Code
- Python 3.10+ (for the installer, graph tooling, and subprocess orchestration)
- [graphify](https://github.com/safishamsi/graphify) on `PATH` (`uv tool install graphifyy` or `pipx install graphifyy`). Set `graph_provider: "builtin"` in `.workflow/config.json` to skip it.
- A local model runtime — [Ollama](https://ollama.com/) is the default. Any OpenAI-compatible endpoint works too.
- Your existing lint / typecheck / test commands

## Roadmap

- [x] `init`, `task`, `status`, `resume`, `replan`, `verify`, `refresh`
- [x] Clarifying questions before planning
- [ ] Parallel step execution where the graph proves independence
- [ ] PR auto-generation (opt-in)
- [ ] Additional graph providers beyond graphify (direct Tree-sitter, LSP)

## License

MIT