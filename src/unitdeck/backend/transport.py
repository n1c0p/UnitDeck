# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Nicola Palmieri (n1c0p)
"""Asynchronous D-Bus transport over QtDBus. Tests replace it with a fake of the same shape."""

from __future__ import annotations

from collections.abc import Callable

from PyQt6.QtCore import QMetaType, QObject, pyqtSlot
from PyQt6.QtDBus import (
    QDBusArgument,
    QDBusConnection,
    QDBusMessage,
    QDBusPendingCallWatcher,
    QDBusPendingReply,
)

SERVICE = "org.freedesktop.systemd1"


class UInt(int):
    """An int that must be sent as D-Bus uint32 (QtDBus would send a plain int as int32)."""


ReplyHandler = Callable[[list], None]
ErrorHandler = Callable[[str, str], None]  # (D-Bus error name, message)
SignalHandler = Callable[[str, list], None]  # (object path, arguments)


class _Receiver(QObject):
    """QtDBus delivers signals only to a slot taking a QDBusMessage."""

    def __init__(self, handler: SignalHandler, parent: QObject) -> None:
        super().__init__(parent)
        self._handler = handler

    @pyqtSlot(QDBusMessage)
    def on_message(self, message: QDBusMessage) -> None:
        self._handler(message.path(), message.arguments())


class QtDBusTransport(QObject):
    def __init__(
        self,
        connection: QDBusConnection,
        *,
        interactive: bool = False,
        timeout_ms: int = -1,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._bus = connection
        self._interactive = interactive
        self._timeout = timeout_ms
        self._pending: set[QDBusPendingCallWatcher] = set()

    def call(
        self,
        path: str,
        interface: str,
        member: str,
        args: list,
        on_reply: ReplyHandler,
        on_error: ErrorHandler,
        service: str = SERVICE,
    ) -> None:
        message = QDBusMessage.createMethodCall(service, path, interface, member)
        message.setArguments([_marshal(arg) for arg in args])
        message.setInteractiveAuthorizationAllowed(self._interactive)
        watcher = QDBusPendingCallWatcher(self._bus.asyncCall(message, self._timeout), self)
        self._pending.add(watcher)

        def finished(done: QDBusPendingCallWatcher) -> None:
            self._pending.discard(done)
            done.deleteLater()
            reply = QDBusPendingReply(done)
            if reply.isError():
                on_error(reply.error().name(), reply.error().message())
            else:
                on_reply(reply.reply().arguments())

        watcher.finished.connect(finished)

    def subscribe(
        self, path: str, interface: str, member: str, handler: SignalHandler, service: str = SERVICE
    ) -> None:
        receiver = _Receiver(handler, self)
        if not self._bus.connect(service, path, interface, member, receiver.on_message):
            raise RuntimeError(f"cannot subscribe to {interface}.{member}")


def _marshal(value: object) -> object:
    """A Python list of str would be sent as 'av' (systemd wants 'as'); UInt becomes uint32."""
    if isinstance(value, UInt):
        return QDBusArgument(int(value), QMetaType.Type.UInt.value)
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return QDBusArgument(value, QMetaType.Type.QStringList.value)
    return value
