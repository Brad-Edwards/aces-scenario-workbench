#!/usr/bin/env python3
"""Repository-side PR title guard.

Single source of truth for this repo's pull-request title policy. The
`.github/workflows/pr-title.yml` CI workflow calls ``validate_pr_title`` here, so
the policy lives in one place.

Policy:
  * Reject agent/tool advertising bracketed prefixes such as ``[codex] ...``,
    ``[claude] ...``, ``[openai] ...``, ``[chatgpt] ...`` (case-insensitive).
  * Enforce the Conventional Commit shape ``<type>(<optional-scope>): <subject>``
    with a single allowed type. release-please reads these commit types to decide
    the version bump.
  * Require the subject to start lowercase (``^[a-z].*$``).

Security: the PR title is untrusted GitHub event data. The CLI reads it from
``$GITHUB_EVENT_PATH`` (parsed as JSON) or the ``PR_TITLE`` env var, never from a
shell-interpolated argument, and never dumps the event payload or environment. It
is intentionally stdlib-only so the CI job runs on a bare ``python`` interpreter.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections.abc import Sequence
from dataclasses import dataclass

#: Agent/tool advertising prefixes banned as a bracketed title prefix.
BRANDED_PREFIXES: tuple[str, ...] = ("codex", "claude", "openai", "chatgpt")

#: Conventional Commit types accepted in PR titles.
CONVENTIONAL_TYPES: tuple[str, ...] = (
    "feat",
    "fix",
    "docs",
    "style",
    "refactor",
    "perf",
    "test",
    "build",
    "ci",
    "chore",
    "revert",
)

#: Subject must start lowercase.
SUBJECT_PATTERN: str = r"^[a-z].*$"

RULE_AGENT_BRAND = "pr-title-agent-brand"
RULE_CONVENTIONAL = "pr-title-conventional"
RULE_SUBJECT_LOWERCASE = "pr-title-subject-lowercase"
RULE_EMPTY = "pr-title-empty"


@dataclass(frozen=True)
class TitleViolation:
    """A single policy violation."""

    rule_id: str
    message: str

    def render(self) -> str:
        return f"[{self.rule_id}] {self.message}"


def _branded_prefix_re(branded_prefixes: Sequence[str]) -> re.Pattern[str]:
    alternation = "|".join(re.escape(p) for p in branded_prefixes)
    return re.compile(rf"^\s*\[\s*(?:{alternation})\s*\]", re.IGNORECASE)


def _conventional_re(types: Sequence[str]) -> re.Pattern[str]:
    alternation = "|".join(re.escape(t) for t in types)
    return re.compile(rf"^(?:{alternation})(?:\([^()\n]+\))?(?:!)?: (?P<subject>.+)$")


def validate_pr_title(
    title: str | None,
    *,
    branded_prefixes: Sequence[str] = BRANDED_PREFIXES,
    types: Sequence[str] = CONVENTIONAL_TYPES,
    subject_pattern: str = SUBJECT_PATTERN,
) -> list[TitleViolation]:
    """Validate ``title`` against the PR title policy and return violations.

    An empty list means the title is acceptable.
    """
    violations: list[TitleViolation] = []
    stripped = (title or "").strip()

    if not stripped:
        violations.append(TitleViolation(RULE_EMPTY, "PR title is empty."))
        return violations

    if _branded_prefix_re(branded_prefixes).match(stripped):
        banned = ", ".join(f"[{p}]" for p in branded_prefixes)
        violations.append(
            TitleViolation(
                RULE_AGENT_BRAND,
                "PR title must not start with an agent/tool advertising prefix "
                f"such as {banned}. Use a project-native conventional title instead.",
            )
        )
        return violations

    match = _conventional_re(types).match(stripped)
    if match is None:
        allowed = ", ".join(types)
        violations.append(
            TitleViolation(
                RULE_CONVENTIONAL,
                "PR title must match '<type>(<optional-scope>): <subject>' with a "
                f"single type from: {allowed}.",
            )
        )
        return violations

    subject = match.group("subject")
    if re.match(subject_pattern, subject) is None:
        violations.append(
            TitleViolation(
                RULE_SUBJECT_LOWERCASE,
                f"PR title subject must start lowercase (match {subject_pattern!r}); "
                f"got subject {subject!r}.",
            )
        )

    return violations


def _resolve_title(args: argparse.Namespace) -> str | None:
    """Resolve the PR title without ever shell-interpolating untrusted data."""
    if args.title is not None:
        return args.title

    event_path = args.event_path or os.environ.get("GITHUB_EVENT_PATH")
    if event_path:
        try:
            with open(event_path, encoding="utf-8") as handle:
                event = json.load(handle)
        except (OSError, json.JSONDecodeError) as exc:
            print(
                f"pr-title-guard: could not read event JSON from {event_path}: {exc}",
                file=sys.stderr,
            )
            return None
        return (event.get("pull_request") or {}).get("title")

    return os.environ.get("PR_TITLE")


def _resolve_author(args: argparse.Namespace) -> str | None:
    """Best-effort PR author login from the event JSON (CI path only)."""
    event_path = args.event_path or os.environ.get("GITHUB_EVENT_PATH")
    if not event_path:
        return None
    try:
        with open(event_path, encoding="utf-8") as handle:
            event = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return None
    return ((event.get("pull_request") or {}).get("user") or {}).get("login")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Repository-side PR title guard.")
    parser.add_argument(
        "--title", default=None, help="PR title to validate directly (local/testing only)."
    )
    parser.add_argument("--event-path", default=None, help="Path to the GitHub event JSON.")
    args = parser.parse_args(argv)

    # Automated authors (e.g. dependabot[bot]) use controlled title formats.
    author = _resolve_author(args)
    if author and author.endswith("[bot]"):
        print(f"pr-title-guard: skipping automated author {author!r}.")
        return 0

    title = _resolve_title(args)
    if title is None:
        print("pr-title-guard: could not resolve a PR title to validate.", file=sys.stderr)
        return 2

    violations = validate_pr_title(title)
    if violations:
        print(f"pr-title-guard: rejected PR title: {title!r}", file=sys.stderr)
        for violation in violations:
            print(f"  {violation.render()}", file=sys.stderr)
        return 1

    print(f"pr-title-guard: OK: {title!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
