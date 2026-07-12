from __future__ import annotations

import os

import aces_scenario_workbench.cli as cli


def _capture(monkeypatch):
    calls: list[list[str]] = []
    monkeypatch.setattr(
        "django.core.management.execute_from_command_line",
        lambda argv: calls.append(list(argv)),
    )
    return calls


def test_no_args_shows_help(monkeypatch):
    calls = _capture(monkeypatch)
    cli.main(["aces-workbench"])
    assert calls == [["aces-workbench", "help"]]


def test_serve_migrates_then_runs(monkeypatch):
    calls = _capture(monkeypatch)
    cli.main(["aces-workbench", "serve"])
    assert calls == [
        ["aces-workbench", "migrate", "--noinput"],
        ["aces-workbench", "runserver", "127.0.0.1:8000"],
    ]


def test_serve_honours_host_and_port(monkeypatch):
    calls = _capture(monkeypatch)
    cli.main(["aces-workbench", "serve", "--host", "myhost", "--port", "9000"])
    assert calls[-1] == ["aces-workbench", "runserver", "myhost:9000"]


def test_createadmin_maps_to_createsuperuser(monkeypatch):
    calls = _capture(monkeypatch)
    cli.main(["aces-workbench", "createadmin"])
    assert calls == [["aces-workbench", "createsuperuser"]]


def test_manage_passthrough(monkeypatch):
    calls = _capture(monkeypatch)
    cli.main(["aces-workbench", "manage", "showmigrations"])
    assert calls == [["aces-workbench", "showmigrations"]]


def test_unknown_command_is_forwarded(monkeypatch):
    calls = _capture(monkeypatch)
    cli.main(["aces-workbench", "migrate"])
    assert calls == [["aces-workbench", "migrate"]]


def test_import_maps_to_import_projection(monkeypatch):
    calls = _capture(monkeypatch)
    cli.main(["aces-workbench", "import", "proj.yaml", "--scenario", "demo"])
    assert calls == [["aces-workbench", "import_projection", "proj.yaml", "--scenario", "demo"]]


def test_serve_defaults_to_debug(monkeypatch):
    # serve is the development runner, so it enables debug mode (which keeps HTTPS
    # enforcement off) unless the environment already sets it.
    monkeypatch.setattr(cli, "_run", lambda argv: None)
    monkeypatch.delenv("ACES_WORKBENCH_DEBUG", raising=False)
    try:
        cli.main(["aces-workbench", "serve"])
        assert os.environ.get("ACES_WORKBENCH_DEBUG") == "true"
    finally:
        os.environ.pop("ACES_WORKBENCH_DEBUG", None)


def test_serve_honours_explicit_debug(monkeypatch):
    monkeypatch.setattr(cli, "_run", lambda argv: None)
    monkeypatch.setenv("ACES_WORKBENCH_DEBUG", "false")
    cli.main(["aces-workbench", "serve"])
    assert os.environ["ACES_WORKBENCH_DEBUG"] == "false"
