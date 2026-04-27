import json

from workflow.validator.detect import detect_validation


def test_detect_typescript_jest_eslint(tmp_path):
    (tmp_path / "package.json").write_text(json.dumps({
        "name": "x",
        "scripts": {"lint": "eslint .", "typecheck": "tsc --noEmit", "test": "jest"},
        "devDependencies": {"typescript": "^5", "eslint": "^8", "jest": "^29"},
    }))

    d = detect_validation(tmp_path)
    assert d["lint"] == "npm run lint"
    assert d["typecheck"] == "npm run typecheck"
    assert d["test"] == "npm test"
    assert "TypeScript" in d["stack"]
    assert "Jest" in d["stack"]
    assert "ESLint" in d["stack"]


def test_detect_python_from_pyproject(tmp_path):
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "x"\n')
    d = detect_validation(tmp_path)
    assert "Python" in d["stack"]
    assert d["test"] == "pytest"
    assert d["lint"] == "ruff check ."


def test_detect_empty_repo(tmp_path):
    d = detect_validation(tmp_path)
    assert d["lint"] is None
    assert d["typecheck"] is None
    assert d["test"] is None
