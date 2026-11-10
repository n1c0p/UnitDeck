# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Nicola Palmieri (n1c0p)
"""systemd-analyze verify for the desktop dialogs, safe against closing the dialog meanwhile."""

from __future__ import annotations

from collections.abc import Callable

from PyQt6 import sip
from PyQt6.QtCore import QObject

from unitdeck.backend import unitfiles
from unitdeck.backend.base import SystemdBackend


def verify(
    owner: QObject, backend: SystemdBackend, staged: str, done: Callable[[int, str], None]
) -> None:
    """Verify the staged copy ``staged`` and call ``done(exit code, relevant lines)``.

    The process belongs to the backend's runtime, not to ``owner``: a dialog closed while the
    check runs no longer destroys a running QProcess under a connected slot, which aborted the
    application (#63). The staging directory is always removed; ``done`` runs only if ``owner``
    still exists, so a closed dialog is left alone.
    """
    args = ["systemd-analyze", *unitfiles.verify_args(backend.scope, staged)]

    def finished(code: int, out: str, err: str) -> None:
        lines = unitfiles.relevant_lines(out + err, staged)
        unitfiles.cleanup_staging(staged)
        if not sip.isdeleted(owner):
            done(code, lines)

    backend.runtime.run(args, None, finished)
