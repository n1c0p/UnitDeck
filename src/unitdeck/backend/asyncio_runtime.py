# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Nicola Palmieri (n1c0p)
"""Runtime for asyncio programs (the terminal interface): dbus-fast transports and subprocesses.

Create it inside a running event loop and ``await runtime.connect()`` before use.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any

from dbus_fast import BusType, Message, MessageFlag, MessageType, Variant
from dbus_fast.aio import MessageBus

from unitdeck.backend.base import ErrorHandler, ProcessDone, ReplyHandler, SignalHandler

SYSTEMD = "org.freedesktop.systemd1"


def unwrap(value: Any) -> Any:
    """dbus-fast wraps variants (a{sv}) in Variant objects; the backend wants plain values."""
    if isinstance(value, Variant):
        return unwrap(value.value)
    if isinstance(value, dict):
        return {k: unwrap(v) for k, v in value.items()}
    if isinstance(value, list):
        return [unwrap(v) for v in value]
    return value


class DbusFastTransport:
    def __init__(self, bus: MessageBus, *, interactive: bool = False) -> None:
        self._bus = bus
        self._interactive = interactive
        self._subscriptions: list[tuple[str, str, str, str, SignalHandler]] = []
        self._tasks: set[asyncio.Task] = set()
        self._closed = False
        bus.add_message_handler(self._on_message)

    def call(
        self,
        path: str,
        interface: str,
        member: str,
        args: list,
        on_reply: ReplyHandler,
        on_error: ErrorHandler,
        service: str = SYSTEMD,
        signature: str = "",
    ) -> None:
        message = Message(
            destination=service,
            path=path,
            interface=interface,
            member=member,
            signature=signature,
            body=[int(a) if isinstance(a, int) and not isinstance(a, bool) else a for a in args],
            flags=MessageFlag.ALLOW_INTERACTIVE_AUTHORIZATION
            if self._interactive
            else MessageFlag.NONE,
        )

        async def send() -> None:
            try:
                reply = await self._bus.call(message)
            except Exception as exc:  # noqa: BLE001 - any failure is reported, never raised
                if not self._closed:
                    on_error(type(exc).__name__, str(exc))
                return
            if self._closed or reply is None:
                return
            if reply.message_type == MessageType.ERROR:
                on_error(reply.error_name or "error", str(reply.body[0]) if reply.body else "")
            else:
                on_reply(unwrap(reply.body))

        self._spawn(send())

    def subscribe(
        self, path: str, interface: str, member: str, handler: SignalHandler, service: str = SYSTEMD
    ) -> None:
        self._subscriptions.append((service, path, interface, member, handler))
        rule = f"type='signal',sender='{service}',interface='{interface}',member='{member}'"
        if path:
            rule += f",path='{path}'"
        self._spawn(
            self._bus.call(
                Message(
                    destination="org.freedesktop.DBus",
                    path="/org/freedesktop/DBus",
                    interface="org.freedesktop.DBus",
                    member="AddMatch",
                    signature="s",
                    body=[rule],
                )
            )
        )

    def close(self) -> None:
        self._closed = True
        self._bus.remove_message_handler(self._on_message)
        self._subscriptions.clear()

    def _on_message(self, message: Message) -> None:
        if message.message_type != MessageType.SIGNAL:
            return
        for _service, path, interface, member, handler in self._subscriptions:
            if message.interface == interface and message.member == member:
                if not path or message.path == path:
                    handler(message.path, unwrap(message.body))

    def _spawn(self, coro) -> None:
        task = asyncio.ensure_future(coro)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)


class AsyncioRuntime:
    """Implements ``unitdeck.backend.base.Runtime`` on asyncio with dbus-fast."""

    def __init__(self) -> None:
        self._buses: dict[BusType, MessageBus] = {}
        self._tasks: set[asyncio.Task] = set()

    async def connect(self) -> None:
        for bus_type in (BusType.SESSION, BusType.SYSTEM):
            if bus_type not in self._buses:
                self._buses[bus_type] = await MessageBus(bus_type=bus_type).connect()

    def transport(self, bus: str, interactive: bool = False) -> DbusFastTransport:
        bus_type = BusType.SYSTEM if bus == "system" else BusType.SESSION
        return DbusFastTransport(self._buses[bus_type], interactive=interactive)

    def schedule(self, delay_ms: int, callback: Callable[[], None]) -> None:
        asyncio.get_running_loop().call_later(delay_ms / 1000, callback)

    def run(self, argv: list[str], stdin: str | None, on_done: ProcessDone) -> None:
        async def go() -> None:
            proc = await asyncio.create_subprocess_exec(
                *argv,
                stdin=asyncio.subprocess.PIPE if stdin is not None else None,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            out, err = await proc.communicate(stdin.encode("utf-8") if stdin is not None else None)
            on_done(
                proc.returncode or 0, out.decode("utf-8", "replace"), err.decode("utf-8", "replace")
            )

        self._spawn(go())

    def stream(
        self,
        argv: list[str],
        on_line: Callable[[bytes], None],
        on_exit: Callable[[int, str], None],
    ) -> Callable[[], None]:
        holder: dict[str, Any] = {}

        async def go() -> None:
            proc = await asyncio.create_subprocess_exec(
                *argv, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            holder["proc"] = proc
            assert proc.stdout is not None and proc.stderr is not None
            async for raw in proc.stdout:
                on_line(raw.rstrip(b"\n"))
            err = (await proc.stderr.read()).decode("utf-8", "replace").strip()
            await proc.wait()
            on_exit(proc.returncode or 0, err)

        task = self._spawn(go())

        def stop() -> None:
            proc = holder.get("proc")
            if proc is not None and proc.returncode is None:
                proc.terminate()
            task.cancel()

        return stop

    def close(self) -> None:
        for bus in self._buses.values():
            bus.disconnect()
        self._buses.clear()

    def _spawn(self, coro) -> asyncio.Task:
        task = asyncio.ensure_future(coro)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return task
