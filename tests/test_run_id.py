from datetime import datetime, timezone

from workflow.util.run_id import make_run_id, slugify


def test_slugify_basic():
    assert slugify("Add Rate Limiting!") == "add-rate-limiting"


def test_slugify_trims_and_collapses():
    assert slugify("  foo   bar-baz  ") == "foo-bar-baz"


def test_make_run_id_dated_slug():
    now = datetime(2026, 4, 20, 10, 0, tzinfo=timezone.utc)
    assert make_run_id("fix login redirect", now) == "2026-04-20-fix-login-redirect"


def test_make_run_id_truncates_long_description():
    now = datetime(2026, 4, 20, 10, 0, tzinfo=timezone.utc)
    long = "a " * 100
    run_id = make_run_id(long, now)
    assert len(run_id) <= len("2026-04-20-") + 40
