from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

from workflow.state.paths import config_path
from workflow.util.fs import exists, read_json, write_json
from workflow.util.log import fatal


DEFAULT_CONFIG: dict[str, Any] = {
    # Metadata fields — consulted by Claude Code slash commands when planning/verifying.
    "planner_model": "claude-opus-4-7",
    "verifier_model": "claude-opus-4-7",
    "graph_provider": "graphify",
    "executor": {
        # Model served by local Ollama. Run `ollama list` to see installed models.
        # Community-recommended models for agentic code editing (2026):
        #   glm-4.7-flash   — best balance of speed/quality, 128K ctx, MoE (3B active/30B total)
        #   qwen3-coder:30b — RL-trained on SWE-Bench, strongest at multi-file edits
        #   qwen2.5-coder:32b — reliable tool calling, good context adherence
        "model": "qwen3.5:latest",
        "timeout_seconds": 600,
        # Metadata: honored by the slash-command orchestrator, not exec-step.
        "max_parallel": 1,
        "max_turns": 12,
        "allowed_tools": ["Read", "Edit", "Write"],
        # Low temperature reduces hallucinated edits; standard for code-edit agents.
        "temperature": 0.1,
        # Context window. Minimum 64K for Claude Code's system prompt overhead.
        # Also set OLLAMA_CONTEXT_LENGTH=65536 in your shell to avoid Ollama
        # silently clamping num_ctx to a smaller value (ollama/ollama#10974).
        "num_ctx": 65536,
    },
    "ask_clarifying_questions": True,
    "always_verify": False,
    "validation": {
        "lint": None,
        "typecheck": None,
        "test": None,
        # Per-phase wall-clock cap in seconds. null disables the timeout.
        "timeout_seconds": 1800,
    },
    # Total attempts per step, including the first try.
    # 4 gives one extra retry to absorb a first bad think-mode response.
    "max_attempts_per_step": 4,
    "max_replans": 2,
}


def load_config(cwd: Path) -> dict[str, Any]:
    p = config_path(cwd)
    if not exists(p):
        fatal("No .workflow/config.json found. Run 'workflow init' first.")
    user = read_json(p)
    return _deep_merge(DEFAULT_CONFIG, user)


def save_config(cwd: Path, config: dict[str, Any]) -> None:
    write_json(config_path(cwd), config)


def config_exists(cwd: Path) -> bool:
    return exists(config_path(cwd))


def _deep_merge(base: Any, over: Any) -> Any:
    """Recursively merge `over` into `base`.

    Dict-vs-dict merges key-by-key. Anything else is replaced wholesale,
    including explicit None overrides — so users can null out a default
    by writing `"key": null` in config.json.
    """
    if isinstance(base, dict) and isinstance(over, dict):
        out = copy.deepcopy(base)
        for k, v in over.items():
            out[k] = _deep_merge(base[k], v) if k in base else copy.deepcopy(v)
        return out
    return copy.deepcopy(over)
