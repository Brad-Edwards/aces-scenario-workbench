"""Tests for the original KeplerOps review prototype."""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
GENERATOR_PATH = REPO_ROOT / "prototype" / "generate_review.py"


def _load_generator():
    spec = importlib.util.spec_from_file_location(
        "keplerops_ai_atlas_review_undertest", GENERATOR_PATH
    )
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


GENERATOR = _load_generator()


class KeplerOpsPrototypeTest(unittest.TestCase):
    def test_render_contains_review_views_and_aces_joins(self) -> None:
        body = GENERATOR.render_site(GENERATOR.load_projection())
        self.assertIn("Technique projection", body)
        self.assertIn("Challenge modules", body)
        self.assertIn("module-01-agent-control", body)
        self.assertIn("AML.T0051.000", body)

    def test_validate_rejects_stale_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "index.html"
            output.write_text("stale", encoding="utf-8")
            failures = GENERATOR.validate(output=output)
        self.assertTrue(any("generated review site is stale" in item for item in failures))

    def test_validate_accepts_generated_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "index.html"
            GENERATOR.generate(output=output)
            self.assertEqual(GENERATOR.validate(output=output), [])


if __name__ == "__main__":
    unittest.main()
