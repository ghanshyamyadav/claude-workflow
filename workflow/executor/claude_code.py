from __future__ import annotations

import os
import shlex
import subprocess
from pathlib import Path


class ClaudeCodeError(RuntimeError):
    pass


def claude_code_execute(
    *,
    cwd: Path,
    prompt: str,
    system: str | None,
    allowed_tools: list[str],
    max_turns: int,
    model: str,
    timeout: float,
    temperature: float | None = None,
    num_ctx: int | None = None,
) -> str:
    """Run Claude Code via `ollama launch claude --model <model> --yes -- -p <prompt> ...`

    Uses ollama's native Claude Code launcher which correctly configures
    ANTHROPIC_BASE_URL, ANTHROPIC_AUTH_TOKEN, and model routing — bypassing
    Claude Code's Anthropic-only model name validation.
    """
    claude_args: list[str] = [
        "-p", prompt,
        "--output-format", "text",
        "--max-turns", str(max_turns),
    ]
    if allowed_tools:
        claude_args += ["--allowedTools", " ".join(allowed_tools)]
    if system:
        claude_args += ["--append-system-prompt", system]

    ollama_args: list[str] = [
        "ollama", "launch", "claude",
        "--model", model,
        "--yes",
    ]
    # `ollama launch claude` does not support --option; num_ctx is controlled via
    # OLLAMA_CONTEXT_LENGTH below. temperature has no equivalent flag here.

    argv: list[str] = [*ollama_args, "--", *claude_args]

    env = os.environ.copy()
    if num_ctx is not None:
        # OLLAMA_CONTEXT_LENGTH is the reliable override; --option num_ctx is silently
        # clamped in some Ollama versions (ollama/ollama#10974).
        env["OLLAMA_CONTEXT_LENGTH"] = str(num_ctx)

    try:
        proc = subprocess.run(
            argv,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
    except FileNotFoundError as err:
        raise ClaudeCodeError(
            "ollama binary not found. Install Ollama and ensure it is on PATH."
        ) from err
    except subprocess.TimeoutExpired as err:
        raise ClaudeCodeError(
            f"ollama launch claude timed out after {timeout}s (model: {model})"
        ) from err

    if proc.returncode != 0:
        tail = (proc.stderr or proc.stdout or "")[-2000:]
        raise ClaudeCodeError(f"claude exited with code {proc.returncode}:\n{tail}")

    return proc.stdout or ""
