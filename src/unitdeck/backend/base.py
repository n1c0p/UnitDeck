# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Nicola Palmieri (n1c0p)
"""Backend interface: plain Python, no GUI toolkit.

The backend talks to systemd through a *runtime* (see ``Runtime``) that a toolkit provides:
Qt for the desktop application, asyncio with dbus-fast for the terminal one. Results reach the
caller through ``Signal`` objects, simple lists of callbacks.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Protocol


class Signal:
    """Minimal observer: ``connect`` a callable, ``emit`` arguments to every connected one."""

    def __init__(self) -> None:
        self._slots: list[Callable[..., Any]] = []

    def connect(self, slot: Callable[..., Any]) -> None:
        self._slots.append(slot)

    def disconnect(self, slot: Callable[..., Any]) -> None:
        self._slots.remove(slot)

    def emit(self, *args: Any) -> None:
        for slot in list(self._slots):
            slot(*args)


class UInt(int):
    """An int that must travel as D-Bus uint32 (a plain int would go as int32)."""


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
ACTIONS = (
    "start",
    "stop",
    "restart",
    "reload",
    "enable",
    "disable",
    "mask",
    "unmask",
    "reset-failed",
    "revert",
)


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
    own: bool = False  # the unit file lives in own_dir (created by the user / administrator)
    vendor_path: str = ""  # same unit shipped elsewhere, when own (so a revert restores it)

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
            case "reset-failed":
                return self.active_state == "failed"
            case "edit":
                return bool(self.fragment_path) and not self.masked
            case "revert":
                return bool(self.drop_in_paths) or (self.own and bool(self.vendor_path))
            case "delete":
                return self.own
            case "logs" | "more":
                return True
        return False


ReplyHandler = Callable[[list], None]
ErrorHandler = Callable[[str, str], None]  # (D-Bus error name, message)
SignalHandler = Callable[[str, list], None]  # (object path, arguments)
ProcessDone = Callable[[int, str, str], None]  # (exit code, stdout, stderr)


class Transport(Protocol):
    """Asynchronous access to one D-Bus bus. Replies arrive through callbacks, never blocking."""

    def call(
        self,
        path: str,
        interface: str,
        member: str,
        args: list,
        on_reply: ReplyHandler,
        on_error: ErrorHandler,
        service: str = "org.freedesktop.systemd1",
        signature: str = "",
    ) -> None: ...

    def subscribe(
        self,
        path: str,
        interface: str,
        member: str,
        handler: SignalHandler,
        service: str = "org.freedesktop.systemd1",
    ) -> None: ...

    def close(self) -> None: ...


class Runtime(Protocol):
    """What a toolkit must provide: buses, a timer and subprocesses, all non-blocking."""

    def transport(self, bus: str, interactive: bool = False) -> Transport:
        """``bus`` is "session" or "user" for the user manager, "system" for the system one."""
        ...

    def schedule(self, delay_ms: int, callback: Callable[[], None]) -> None: ...

    def run(self, argv: list[str], stdin: str | None, on_done: ProcessDone) -> None: ...

    def stream(
        self,
        argv: list[str],
        on_line: Callable[[bytes], None],
        on_exit: Callable[[int, str], None],
    ) -> Callable[[], None]:
        """Start a process and deliver its stdout line by line; returns a stop() callable."""
        ...


class SystemdBackend:
    """One systemd manager, system or user.

    Every call is asynchronous: results arrive through the signals below, the caller never blocks.
    """

    def __init__(self, scope: Scope, runtime: Runtime) -> None:
        self.scope = scope
        self.runtime = runtime
        self.own_dir = own_unit_dir(scope)
        self.units: dict[str, Unit] = {}
        self.busy: set[str] = set()
        self.units_changed = Signal()  # self.units was rebuilt
        self.unit_updated = Signal()  # (name): one unit changed in place
        self.busy_changed = Signal()  # (name, busy): an operation on that unit started / ended
        self.operation_finished = Signal()  # (unit "" = manager, action, ok, detail)
        self.writer: Any = None  # UnitWriter, set by the concrete backends

    def refresh(self) -> None:
        """Reload the whole unit list; emits units_changed."""
        raise NotImplementedError

    def fetch_details(self, name: str) -> None:
        """Fill can_reload and drop_in_paths of a unit; emits unit_updated."""
        raise NotImplementedError

    def run(self, action: str, name: str) -> None:
        """Run one of ACTIONS on a unit; emits busy_changed and operation_finished."""
        raise NotImplementedError

    def daemon_reload(self) -> None:
        raise NotImplementedError

    def close(self) -> None:
        """Stop listening to the bus; the object is not usable afterwards."""
