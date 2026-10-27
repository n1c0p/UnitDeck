# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Nicola Palmieri (n1c0p)
"""Journal reader: ``journalctl -o json`` through the runtime, one entry per line."""

from __future__ import annotations

import datetime
import json
from collections.abc import Callable

from unitdeck.backend.base import Runtime, Scope, Signal

PRIORITIES = ("emerg", "alert", "crit", "err", "warning", "notice", "info", "debug")


def journalctl_args(unit: str, scope: Scope, lines: int, priority: int, follow: bool) -> list[str]:
    args = ["--no-pager", "-o", "json", "-u", unit, "-n", str(lines), "-p", str(priority)]
    if scope is Scope.USER:
        args.append("--user")
    if follow:
        args.append("-f")
    return args


def format_entry(entry: dict) -> tuple[str, int]:
    """One journal JSON object -> (text line, priority 0-7)."""
    try:
        micros = int(entry["__REALTIME_TIMESTAMP"])
        stamp = datetime.datetime.fromtimestamp(micros / 1e6).strftime("%Y-%m-%d %H:%M:%S")
    except (KeyError, ValueError, OverflowError, OSError):
        stamp = "????-??-?? ??:??:??"
    try:
        priority = int(entry.get("PRIORITY", 6))
    except (TypeError, ValueError):
        priority = 6
    message = entry.get("MESSAGE", "")
    if isinstance(message, list):  # non-UTF-8 payloads arrive as byte arrays
        message = bytes(message).decode("utf-8", "replace")
    ident = entry.get("SYSLOG_IDENTIFIER") or entry.get("_COMM") or ""
    return (f"{stamp} {ident}: {message}" if ident else f"{stamp} {message}"), priority


class JournalReader:
    def __init__(self, runtime: Runtime) -> None:
        self._runtime = runtime
        self._stop: Callable[[], None] | None = None
        self.entry = Signal()  # (line, priority)
        self.finished = Signal()  # (exit code, stderr)

    def start(self, unit: str, scope: Scope, lines: int, priority: int, follow: bool) -> None:
        self.stop()
        args = ["journalctl", *journalctl_args(unit, scope, lines, priority, follow)]
        self._stop = self._runtime.stream(args, self._on_line, self._on_exit)

    def stop(self) -> None:
        if self._stop is not None:
            stop, self._stop = self._stop, None
            stop()

    def _on_line(self, raw: bytes) -> None:
        if not raw.strip():
            return
        try:
            entry = json.loads(raw)
        except ValueError:
            return
        self.entry.emit(*format_entry(entry))

    def _on_exit(self, code: int, stderr: str) -> None:
        self._stop = None
        self.finished.emit(code, stderr)
