# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Nicola Palmieri (n1c0p)
"""Journal reader: ``journalctl -o json`` through QProcess, one entry per line."""

from __future__ import annotations

import datetime
import json

from PyQt6.QtCore import QObject, QProcess, pyqtSignal

from unitdeck.backend.base import Scope

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


class JournalReader(QObject):
    entry = pyqtSignal(str, int)  # line, priority
    finished = pyqtSignal(int, str)  # exit code, stderr

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._buffer = b""
        self._proc = QProcess(self)
        self._proc.readyReadStandardOutput.connect(self._read)
        self._proc.finished.connect(self._on_finished)

    def start(self, unit: str, scope: Scope, lines: int, priority: int, follow: bool) -> None:
        self.stop()
        self._buffer = b""
        self._proc.start("journalctl", journalctl_args(unit, scope, lines, priority, follow))

    def stop(self) -> None:
        if self._proc.state() != QProcess.ProcessState.NotRunning:
            self._proc.terminate()
            if not self._proc.waitForFinished(1000):
                self._proc.kill()

    def _read(self) -> None:
        self._buffer += bytes(self._proc.readAllStandardOutput())
        *lines, self._buffer = self._buffer.split(b"\n")
        for raw in lines:
            if not raw.strip():
                continue
            try:
                entry = json.loads(raw)
            except ValueError:
                continue
            self.entry.emit(*format_entry(entry))

    def _on_finished(self, code: int, _status: object) -> None:
        stderr = bytes(self._proc.readAllStandardError()).decode("utf-8", "replace").strip()
        self.finished.emit(code, stderr)
