from __future__ import annotations

import importlib.metadata

import aces_scenario_workbench


def test_version_is_a_string():
    assert isinstance(aces_scenario_workbench.__version__, str)
    assert aces_scenario_workbench._package_version()


def test_version_falls_back_when_uninstalled(monkeypatch):
    def raise_not_found(name):
        raise importlib.metadata.PackageNotFoundError(name)

    monkeypatch.setattr(aces_scenario_workbench, "version", raise_not_found)
    assert aces_scenario_workbench._package_version() == "0.0.0"
