# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Nicola Palmieri (n1c0p)
"""Simulated D-Bus: canned replies per method, synchronous callbacks, recorded calls."""


class DBusError(Exception):
    def __init__(self, name: str, message: str) -> None:
        super().__init__(message)
        self.name = name


class FakeTransport:
    def __init__(self, replies: dict | None = None) -> None:
        self.replies = replies or {}  # member -> reply arguments list, or DBusError
        self.calls: list[tuple[str, str, str, list]] = []
        self.handlers: dict[str, object] = {}

    def call(self, path, interface, member, args, on_reply, on_error, service=None) -> None:
        self.calls.append((path, interface, member, args))
        reply = self.replies.get(member, [])
        if isinstance(reply, DBusError):
            on_error(reply.name, str(reply))
        else:
            on_reply(reply)

    def subscribe(self, path, interface, member, handler, service=None) -> None:
        self.handlers[member] = handler

    def emit(self, member: str, path: str, args: list) -> None:
        self.handlers[member](path, args)

    def members(self) -> list[str]:
        return [call[2] for call in self.calls]
