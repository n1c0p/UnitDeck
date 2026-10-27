# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Nicola Palmieri (n1c0p)
"""User lingering through logind: whether user services keep running without a session."""

from __future__ import annotations

import os

from unitdeck.backend.base import Signal, Transport, UInt

LOGIN1 = "org.freedesktop.login1"
LOGIN1_PATH = "/org/freedesktop/login1"
MANAGER_IFACE = "org.freedesktop.login1.Manager"
USER_IFACE = "org.freedesktop.login1.User"
PROPERTIES_IFACE = "org.freedesktop.DBus.Properties"


class LingerControl:
    """``transport`` must be on the system bus with interactive authorization (polkit may ask)."""

    def __init__(self, transport: Transport, uid: int | None = None) -> None:
        self._t = transport
        self._uid = os.getuid() if uid is None else uid
        self._user_path = ""
        self.changed = Signal()  # (enabled)
        self.failed = Signal()  # ("error.name: message")

    def refresh(self) -> None:
        if self._user_path:
            self._read()
            return
        args = [UInt(self._uid)]
        self._t.call(
            LOGIN1_PATH, MANAGER_IFACE, "GetUser", args, self._on_user, self._error, LOGIN1, "u"
        )

    def set_linger(self, enabled: bool) -> None:
        self._t.call(
            LOGIN1_PATH,
            MANAGER_IFACE,
            "SetUserLinger",
            [UInt(self._uid), bool(enabled), True],  # interactive authorization
            lambda _args: self.refresh(),
            self._error,
            LOGIN1,
            "ubb",
        )

    def close(self) -> None:
        self._t.close()

    def _on_user(self, args: list) -> None:
        self._user_path = args[0]
        self._t.subscribe(
            self._user_path, PROPERTIES_IFACE, "PropertiesChanged", self._on_props, LOGIN1
        )
        self._read()

    def _read(self) -> None:
        self._t.call(
            self._user_path,
            PROPERTIES_IFACE,
            "Get",
            [USER_IFACE, "Linger"],
            lambda args: self.changed.emit(bool(args[0])),
            self._error,
            LOGIN1,
            "ss",
        )

    def _on_props(self, _path: str, args: list) -> None:
        if args[0] == USER_IFACE and "Linger" in args[1]:
            self.changed.emit(bool(args[1]["Linger"]))

    def _error(self, error: str, message: str) -> None:
        self.failed.emit(f"{error}: {message}")
