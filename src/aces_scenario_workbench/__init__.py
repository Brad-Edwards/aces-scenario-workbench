"""ACES Scenario Workbench — collaborative review surface for ACES scenario packs."""

from importlib.metadata import PackageNotFoundError, version


def _package_version() -> str:
    """Version from installed metadata (pyproject [project].version, bumped by release-please)."""
    try:
        return version("aces-scenario-workbench")
    except PackageNotFoundError:
        return "0.0.0"


__version__ = _package_version()
