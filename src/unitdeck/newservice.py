# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Nicola Palmieri (n1c0p)
"""Rules of the new-service wizard shared by the desktop and terminal interfaces."""

from __future__ import annotations

import os
import re

from unitdeck.backend import unitfiles
from unitdeck.backend.base import SystemdBackend
from unitdeck.i18n import tr

NAME_RE = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_.:-]{0,245}$")
TYPES = ("simple", "exec", "forking", "oneshot", "dbus", "notify", "idle")
RESTARTS = ("no", "on-success", "on-failure", "on-abnormal", "on-abort", "always")
LABELS = {  # placeholder -> field label (source strings, translated with tr())
    "DESCRIPTION": "Description",
    "TYPE": "Type",
    "EXEC_START": "Command (ExecStart)",
    "EXEC_STOP": "Stop command (ExecStop)",
    "RESTART": "Restart policy (Restart)",
    "AFTER": "Start after (After)",
    "WANTS": "Wants",
    "USER": "User",
    "GROUP": "Group",
    "WANTED_BY": "Wanted by (WantedBy)",
    "SERVER": "Server",
    "SHARE": "Share",
    "CREDENTIALS_FILE": "Credentials file (relative to home)",
}
REQUIRED = ("EXEC_START", "SERVER", "SHARE", "CREDENTIALS_FILE")


def placeholder_label(name: str) -> str:
    return tr(LABELS[name]) if name in LABELS else name.replace("_", " ").capitalize()


def normalize_name(text: str) -> str:
    text = text.strip()
    return text if text.endswith(".service") or not text else text + ".service"


def name_problem(name: str, backend: SystemdBackend) -> str:
    """'' when the name is valid and free in every systemd search path, else the reason."""
    stem = name[: -len(".service")] if name.endswith(".service") else name
    if not NAME_RE.match(stem):
        return tr("Use letters, digits, '-', '_', '.' and ':' only.")
    if name in backend.units or os.path.lexists(unitfiles.unit_path(name, backend.own_dir)):
        return tr("A unit with this name already exists.")
    for directory in unitfiles.OTHER_UNIT_DIRS[backend.scope]:
        if os.path.lexists(os.path.join(directory, name)):
            return tr("A unit with this name already exists.")
    return ""
