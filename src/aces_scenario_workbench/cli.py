"""Console entry point for the ACES Scenario Workbench.

Wraps Django's management command runner with a few friendly aliases so the
workbench can be stood up from a single ``aces-workbench`` command.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Sequence


def _run(argv: list[str]) -> None:
    from django.core.management import execute_from_command_line

    execute_from_command_line(argv)


def _serve(args: list[str]) -> None:
    host = os.environ.get("ACES_WORKBENCH_HOST", "127.0.0.1")
    port = os.environ.get("ACES_WORKBENCH_PORT", "8000")
    it = iter(args)
    for token in it:
        if token in {"--host", "-b"}:
            host = next(it, host)
        elif token in {"--port", "-p"}:
            port = next(it, port)
    # Apply migrations first so a fresh install serves immediately.
    _run(["aces-workbench", "migrate", "--noinput"])
    _run(["aces-workbench", "runserver", f"{host}:{port}"])


def main(argv: Sequence[str] | None = None) -> None:
    argv = list(sys.argv if argv is None else argv)
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aces_scenario_workbench.settings")

    args = argv[1:]
    if not args:
        _run(["aces-workbench", "help"])
        return

    command, rest = args[0], args[1:]
    if command == "serve":
        _serve(rest)
    elif command == "createadmin":
        _run(["aces-workbench", "createsuperuser", *rest])
    elif command == "manage":
        _run(["aces-workbench", *rest])
    else:
        _run(["aces-workbench", *args])
