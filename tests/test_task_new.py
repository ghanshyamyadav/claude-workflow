import io
import json

import pytest

from workflow.commands import task_new
from workflow.state.run import load_state


def _latest_run_id(capsys) -> str:
    captured = capsys.readouterr()
    return captured.out.strip().splitlines()[-1]


def test_task_new_accepts_inline_json(tmp_path, capsys):
    task_new.run(
        cwd=tmp_path,
        description="do stuff",
        clarifications='[{"q":"scope?","a":"small"}]',
    )
    run_id = _latest_run_id(capsys)
    state = load_state(tmp_path, run_id)
    assert state["description"] == "do stuff"


def test_task_new_reads_clarifications_file(tmp_path, capsys):
    f = tmp_path / "clar.json"
    f.write_text(json.dumps([{"q": "has 'quotes' and \"doubles\"", "a": "ok"}]))

    task_new.run(
        cwd=tmp_path,
        description="quoting case",
        clarifications="[]",  # should be ignored in favor of the file
        clarifications_file=str(f),
    )
    run_id = _latest_run_id(capsys)
    task_md = (tmp_path / ".workflow" / "runs" / run_id / "task.md").read_text()
    assert "has 'quotes' and \"doubles\"" in task_md


def test_task_new_reads_clarifications_stdin(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(
        "sys.stdin",
        io.StringIO(json.dumps([{"q": "from stdin?", "a": "yes"}])),
    )
    task_new.run(
        cwd=tmp_path,
        description="stdin case",
        clarifications="[]",
        clarifications_file="-",
    )
    run_id = _latest_run_id(capsys)
    task_md = (tmp_path / ".workflow" / "runs" / run_id / "task.md").read_text()
    assert "from stdin?" in task_md


def test_task_new_rejects_non_array_clarifications(tmp_path):
    import click
    with pytest.raises(click.ClickException, match="JSON array"):
        task_new.run(
            cwd=tmp_path,
            description="oops",
            clarifications='{"not": "an array"}',
        )
