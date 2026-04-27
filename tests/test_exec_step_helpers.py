from workflow.commands.exec_step import _diff_out_of_scope, _max_attempts


def test_diff_out_of_scope_ignores_files_changed_before_the_step():
    pre = {"src/a.ts"}
    post = {"src/a.ts", "src/b.ts"}
    assert _diff_out_of_scope(pre, post, in_scope=["src/b.ts"]) == []


def test_diff_out_of_scope_flags_new_files_not_in_scope():
    pre = {"src/a.ts"}
    post = {"src/a.ts", "src/b.ts", "src/c.ts"}
    assert _diff_out_of_scope(pre, post, in_scope=["src/b.ts"]) == ["src/c.ts"]


def test_diff_out_of_scope_returns_sorted_list():
    pre = set()
    post = {"z.ts", "a.ts", "m.ts"}
    assert _diff_out_of_scope(pre, post, in_scope=[]) == ["a.ts", "m.ts", "z.ts"]


def test_max_attempts_defaults_to_three():
    assert _max_attempts({}) == 3


def test_max_attempts_reads_config_key():
    assert _max_attempts({"max_attempts_per_step": 5}) == 5


def test_max_attempts_clamps_to_at_least_one():
    assert _max_attempts({"max_attempts_per_step": 0}) == 1
    assert _max_attempts({"max_attempts_per_step": -7}) == 1


def test_max_attempts_ignores_garbage_values():
    assert _max_attempts({"max_attempts_per_step": "abc"}) == 3
