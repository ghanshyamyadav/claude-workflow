from workflow.executor.prompt import build_claude_code_prompt, parse_termination


def test_prompt_contains_scope_and_files():
    prompt = build_claude_code_prompt(
        step={"num": 2, "title": "Register middleware", "description": "wire the limiter"},
        files_in_scope=["src/app.ts", "src/middleware.ts"],
    )
    assert "wire the limiter" in prompt
    assert "src/app.ts" in prompt
    assert "src/middleware.ts" in prompt
    assert "NEEDS_REPLAN" in prompt
    assert "DONE" in prompt


def test_prompt_does_not_inline_file_contents():
    prompt = build_claude_code_prompt(
        step={"num": 1, "title": "x"},
        files_in_scope=["a.ts"],
    )
    assert "```" not in prompt  # CC reads files itself; no inline content


def test_prompt_empty_scope_calls_out_replan_guidance():
    prompt = build_claude_code_prompt(
        step={"num": 1, "title": "x"},
        files_in_scope=[],
    )
    assert "Do not modify any file" in prompt


def test_prompt_retry_section_included_when_error_present():
    prompt = build_claude_code_prompt(
        step={"num": 1, "title": "x"},
        files_in_scope=["a.ts"],
        retry_error="TypeError: undefined is not a function",
    )
    assert "Previous attempt failed" in prompt
    assert "TypeError" in prompt


def test_parse_termination_done():
    assert parse_termination("some work done\nDONE")["kind"] == "done"


def test_parse_termination_done_ignores_trailing_blank_lines():
    assert parse_termination("DONE\n\n  \n")["kind"] == "done"


def test_parse_termination_needs_replan_with_reason():
    r = parse_termination("hmm\nNEEDS_REPLAN: file xyz missing")
    assert r["kind"] == "needs_replan"
    assert r["reason"] == "file xyz missing"


def test_parse_termination_missing_when_neither():
    assert parse_termination("just some prose with no terminator")["kind"] == "missing"


def test_parse_termination_missing_when_empty():
    assert parse_termination("")["kind"] == "missing"
