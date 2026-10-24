# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Nicola Palmieri (n1c0p)
"""Backend interface. Depends on QtCore only, never on the GUI."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import StrEnum

from PyQt6.QtCore import QObject, pyqtSignal


class Scope(StrEnum):
    SYSTEM = "system"
    USER = "user"


def own_unit_dir(scope: Scope) -> str:
    """Directory holding the units created by the administrator (system) or the user."""
    if scope is Scope.SYSTEM:
        return "/etc/systemd/system"
    config = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    return os.path.join(config, "systemd", "user")


RUNNING_STATES = frozenset({"active", "reloading", "activating", "refreshing"})

# Actions a unit can be asked for; "logs" and "more" are GUI-only and always available.
ACTIONS = ("start", "stop", "restart", "reload", "enable", "disable", "mask", "unmask")


@dataclass(slots=True)
class Unit:
    name: str
    description: str = ""
    load_state: str = ""  # "" when the unit file exists but the unit is not loaded
    active_state: str = "inactive"
    sub_state: str = "dead"
    unit_file_state: str = ""  # "" for transient units without a file
    fragment_path: str = ""
    object_path: str = ""  # "" when not loaded
    can_reload: bool | None = None  # None until fetch_details() has answered
    drop_in_paths: list[str] = field(default_factory=list)

    @property
    def loaded(self) -> bool:
        return bool(self.object_path)

    @property
    def running(self) -> bool:
        return self.active_state in RUNNING_STATES

    @property
    def masked(self) -> bool:
        return self.load_state == "masked" or self.unit_file_state.startswith("masked")

    def can(self, action: str) -> bool:
        match action:
            case "start":
                return not self.running and not self.masked
            case "stop" | "restart":
                return self.running
            case "reload":
                return self.running and bool(self.can_reload)
            case "enable":
                return self.unit_file_state == "disabled"
            case "disable":
                return self.unit_file_state in ("enabled", "enabled-runtime")
            case "mask":
                return not self.masked and self.unit_file_state != ""
            case "unmask":
                return self.masked
            case "logs" | "more":
                return True
        return False


class SystemdBackend(QObject):
    """One systemd manager, system or user.

    Every call is asynchronous: results arrive through the signals below, the GUI never blocks.
    """

    units_changed = pyqtSignal()  # self.units was rebuilt
    unit_updated = pyqtSignal(str)  # one unit changed in place
    busy_changed = pyqtSignal(str, bool)  # an operation on that unit started / ended
    operation_finished = pyqtSignal(str, str, bool, str)  # unit ("" = manager), action, ok, detail

    def __init__(self, scope: Scope, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.scope = scope
        self.own_dir = own_unit_dir(scope)
        self.units: dict[str, Unit] = {}
        self.busy: set[str] = set()

    def refresh(self) -> None:
        """Reload the whole unit list; emits units_changed."""
        raise NotImplementedError

    def fetch_details(self, name: str) -> None:
        """Fill can_reload and drop_in_paths of a loaded unit; emits unit_updated."""
        raise NotImplementedError

    def run(self, action: str, name: str) -> None:
        """Run one of ACTIONS on a unit; emits busy_changed and operation_finished."""
        raise NotImplementedError

    def daemon_reload(self) -> None:
        raise NotImplementedError
