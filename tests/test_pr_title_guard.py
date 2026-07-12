from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_guard():
    spec = importlib.util.spec_from_file_location(
        "check_pr_title", _REPO_ROOT / "tools" / "check_pr_title.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    # Register before exec so the dataclass can resolve annotations.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


guard = _load_guard()


def test_accepts_conventional_titles():
    assert guard.validate_pr_title("feat: add the review surface") == []
    assert guard.validate_pr_title("fix(ingest): handle empty projection") == []


def test_rejects_branded_prefix():
    violations = guard.validate_pr_title("[claude] feat: add thing")
    assert any(v.rule_id == "pr-title-agent-brand" for v in violations)


def test_rejects_non_conventional():
    assert guard.validate_pr_title("Add a thing")


def test_rejects_uppercase_subject():
    violations = guard.validate_pr_title("feat: Add thing")
    assert any(v.rule_id == "pr-title-subject-lowercase" for v in violations)


def test_rejects_empty():
    violations = guard.validate_pr_title("")
    assert any(v.rule_id == "pr-title-empty" for v in violations)
