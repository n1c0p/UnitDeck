# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Nicola Palmieri (n1c0p)
"""Polkit from a terminal: without a graphical session, pkttyagent asks for the password."""

from __future__ import annotations

import os
import shutil
import subprocess


def graphical_session() -> bool:
    return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))


class TtyAgent:
    """Registers pkttyagent for this process while the block runs (what systemctl does on a TTY)."""

    def __init__(self) -> None:
        self._proc: subprocess.Popen | None = None

    def __enter__(self) -> TtyAgent:
        if shutil.which("pkttyagent"):
            self._proc = subprocess.Popen(["pkttyagent", "--process", str(os.getpid())])
        return self

    def __exit__(self, *_exc: object) -> None:
        if self._proc is not None and self._proc.poll() is None:
            self._proc.terminate()
            try:
                self._proc.wait(2)
            except subprocess.TimeoutExpired:
                self._proc.kill()
        self._proc = None
