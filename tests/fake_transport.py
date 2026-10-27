# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Nicola Palmieri (n1c0p)
"""Simulated D-Bus and runtime: canned replies per method, synchronous callbacks, recorded calls."""


class DBusError(Exception):
    def __init__(self, name: str, message: str) -> None:
        super().__init__(message)
        self.name = name


class FakeTransport:
    def __init__(self, replies: dict | None = None) -> None:
        self.replies = replies or {}  # member -> reply arguments list, or DBusError
        self.calls: list[tuple[str, str, str, list]] = []
        self.signatures: dict[str, str] = {}  # member -> last signature given
        self.handlers: dict[str, object] = {}
        self.closed = False

    def call(self, path, interface, member, args, on_reply, on_error, service=None, signature=""):
        self.calls.append((path, interface, member, args))
        self.signatures[member] = signature
        reply = self.replies.get(member, [])
        if isinstance(reply, DBusError):
            on_error(reply.name, str(reply))
        else:
            on_reply(reply)

    def subscribe(self, path, interface, member, handler, service=None) -> None:
        self.handlers[member] = handler

    def close(self) -> None:
        self.closed = True

    def emit(self, member: str, path: str, args: list) -> None:
        self.handlers[member](path, args)

    def members(self) -> list[str]:
        return [call[2] for call in self.calls]


class FakeRuntime:
    """Timers fire when the test calls ``fire()``; processes answer with canned results."""

    def __init__(self, transport: FakeTransport | None = None, process_results=None) -> None:
        self._transport = transport or FakeTransport()
        self.scheduled: list[tuple[int, object]] = []
        self.processes: list[tuple[list[str], str | None]] = []
        self.process_results = list(process_results or [])  # (code, stdout, stderr) per run()

    def transport(self, bus: str, interactive: bool = False):
        return self._transport

    def schedule(self, delay_ms: int, callback) -> None:
        self.scheduled.append((delay_ms, callback))

    def fire(self) -> None:
        pending, self.scheduled = self.scheduled, []
        for _delay, callback in pending:
            callback()

    def run(self, argv, stdin, on_done) -> None:
        self.processes.append((argv, stdin))
        code, out, err = self.process_results.pop(0) if self.process_results else (0, "", "")
        on_done(code, out, err)

    def stream(self, argv, on_line, on_exit):
        self.processes.append((argv, None))
        return lambda: None
