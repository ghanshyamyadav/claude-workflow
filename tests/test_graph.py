import json

from workflow.graph.builder import build_graph
from workflow.graph.summarize import summarize_file


def test_summarize_extracts_imports_and_symbols(tmp_path):
    f = tmp_path / "x.ts"
    f.write_text(
        "import { foo } from './foo';\n"
        "import React from 'react';\n"
        "\n"
        "export function hello() { return 1; }\n"
        "export class Widget {}\n"
    )
    s = summarize_file(f, "x.ts")
    assert "./foo" in s["imports"]
    assert "react" in s["imports"]
    assert "hello" in s["symbols"]
    assert "Widget" in s["symbols"]


def test_build_graph_ignores_node_modules_and_writes_artifacts(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "node_modules" / "foo").mkdir(parents=True)
    (tmp_path / "src" / "a.ts").write_text("export const a = 1;\n")
    (tmp_path / "node_modules" / "foo" / "index.js").write_text("module.exports = {};\n")

    result = build_graph(tmp_path)
    assert result["files"] == 1

    index = json.loads((tmp_path / ".workflow" / "graph" / "index.json").read_text())
    assert len(index["files"]) == 1
    assert index["files"][0]["path"].endswith("a.ts")

    summary = (tmp_path / ".workflow" / "repo_summary.md").read_text()
    assert "# Repo summary" in summary
    assert "a.ts" in summary
