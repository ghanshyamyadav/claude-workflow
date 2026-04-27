from workflow.validator.runner import run_validation


def test_skipped_when_phase_command_is_null(tmp_path):
    result = run_validation(tmp_path, {"lint": None, "typecheck": None, "test": None})
    assert result["ok"] is True
    names = [r["name"] for r in result["results"] if r["skipped"]]
    assert names == ["lint", "typecheck", "test"]


def test_stops_on_first_failure(tmp_path):
    result = run_validation(
        tmp_path,
        {"lint": "false", "typecheck": "echo should-not-run", "test": "echo nope"},
    )
    assert result["ok"] is False
    # Only lint ran; typecheck + test are still recorded as skipped defaults.
    lint = next(r for r in result["results"] if r["name"] == "lint")
    assert lint["ok"] is False
    assert len(result["results"]) == 1


def test_times_out_long_running_phase(tmp_path):
    result = run_validation(
        tmp_path,
        {"lint": "sleep 5", "timeout_seconds": 0.2},
    )
    assert result["ok"] is False
    lint = next(r for r in result["results"] if r["name"] == "lint")
    assert "timed out" in lint["output"]


def test_null_timeout_disables_limit(tmp_path):
    # We just verify it doesn't crash when timeout is null; a fast command still returns.
    result = run_validation(tmp_path, {"lint": "true", "timeout_seconds": None})
    assert result["ok"] is True
