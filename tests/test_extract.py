import pytest

from workflow.patch.extract import extract_diff


def test_extracts_fenced_diff_block():
    raw = "here:\n```diff\n--- a/x.ts\n+++ b/x.ts\n@@ -1 +1 @@\n-a\n+b\n```\ndone."
    diff = extract_diff(raw)
    assert diff.startswith("--- a/x.ts\n+++ b/x.ts\n")
    assert diff.endswith("\n")


def test_extracts_unlabelled_fence_when_contents_look_like_diff():
    raw = "```\ndiff --git a/x b/x\n--- a/x\n+++ b/x\n@@ -1 +1 @@\n-a\n+b\n```"
    diff = extract_diff(raw)
    assert diff.startswith("diff --git")


def test_accepts_bare_diff():
    raw = "--- a/x\n+++ b/x\n@@ -1 +1 @@\n-a\n+b\n"
    assert extract_diff(raw).startswith("--- a/x")


def test_rejects_non_diff():
    with pytest.raises(ValueError, match="no unified diff"):
        extract_diff("no diff here at all")


def test_rejects_empty():
    with pytest.raises(ValueError, match="empty"):
        extract_diff("")


def test_prefers_diff_fence_even_when_another_fence_appears_first():
    raw = (
        "First, some context:\n"
        "```\n"
        "not a diff at all\n"
        "```\n"
        "Then the actual patch:\n"
        "```diff\n"
        "--- a/x\n"
        "+++ b/x\n"
        "@@ -1 +1 @@\n"
        "-a\n"
        "+b\n"
        "```\n"
    )
    diff = extract_diff(raw)
    assert diff.startswith("--- a/x")


def test_falls_through_unlabelled_non_diff_fence_to_later_unlabelled_diff():
    raw = (
        "```\n"
        "echo hi\n"
        "```\n"
        "```\n"
        "--- a/x\n"
        "+++ b/x\n"
        "@@ -1 +1 @@\n"
        "-a\n"
        "+b\n"
        "```\n"
    )
    diff = extract_diff(raw)
    assert diff.startswith("--- a/x")
