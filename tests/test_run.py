from workflow.state.run import (
    create_run,
    find_resumable_run,
    list_runs,
    load_state,
    next_pending_step,
    save_plan,
)


def test_create_run_save_plan_and_resume(tmp_path):
    run_id = "2026-04-20-test"
    create_run(
        tmp_path,
        run_id=run_id,
        description="do a thing",
        clarifications=[{"q": "scope?", "a": "small"}],
    )

    state = load_state(tmp_path, run_id)
    assert state["status"] == "planning"
    assert state["steps"] == []

    save_plan(tmp_path, run_id, {
        "steps": [
            {"title": "one", "files": ["a.ts"]},
            {"title": "two", "files": ["b.ts"]},
        ],
    })

    state = load_state(tmp_path, run_id)
    assert state["status"] == "in_progress"
    assert len(state["steps"]) == 2
    assert state["current_step"] == 1
    assert next_pending_step(state)["title"] == "one"

    runs = list_runs(tmp_path)
    assert len(runs) == 1
    assert runs[0]["id"] == run_id

    resumable = find_resumable_run(tmp_path)
    assert resumable["id"] == run_id

    task_md = (tmp_path / ".workflow" / "runs" / run_id / "task.md").read_text()
    assert "do a thing" in task_md
    assert "scope?" in task_md
