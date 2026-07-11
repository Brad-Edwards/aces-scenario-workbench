from __future__ import annotations

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
