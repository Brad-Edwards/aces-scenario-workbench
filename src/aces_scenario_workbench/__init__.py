"""ACES Scenario Workbench — collaborative review surface for ACES scenario packs."""

from importlib.metadata import PackageNotFoundError, version

try:
    # The version lives in pyproject.toml ([project].version), bumped by
    # release-please; __version__ derives from the installed package metadata.
    __version__ = version("aces-scenario-workbench")
except PackageNotFoundError:  # pragma: no cover - only when running uninstalled
    __version__ = "0.0.0"
