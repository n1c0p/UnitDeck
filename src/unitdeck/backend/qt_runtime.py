# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Nicola Palmieri (n1c0p)
"""Runtime for the Qt application: QtDBus transports, QTimer and QProcess."""

from __future__ import annotations

from collections.abc import Callable

from PyQt6.QtCore import QMetaType, QObject, QProcess, QTimer, pyqtSlot
from PyQt6.QtDBus import (
    QDBusArgument,
    QDBusConnection,
    QDBusMessage,
    QDBusPendingCallWatcher,
    QDBusPendingReply,
)

from unitdeck.backend.base import (
    ErrorHandler,
    ProcessDone,
    ReplyHandler,
    SignalHandler,
    UInt,
)

SYSTEMD = "org.freedesktop.systemd1"
POLKIT_TIMEOUT_MS = 10 * 60 * 1000  # QtDBus defaults to 25 s: too short for a polkit dialog


class _Receiver(QObject):
    """QtDBus delivers signals only to a slot taking a QDBusMessage."""

    def __init__(self, handler: SignalHandler, parent: QObject) -> None:
        super().__init__(parent)
        self._handler = handler

    @pyqtSlot(QDBusMessage)
    def on_message(self, message: QDBusMessage) -> None:
        self._handler(message.path(), message.arguments())


class QtDBusTransport(QObject):
    def __init__(self, connection: QDBusConnection, *, interactive: bool = False) -> None:
        super().__init__()
        self._bus = connection
        self._interactive = interactive
        self._timeout = POLKIT_TIMEOUT_MS if interactive else -1
        self._pending: set[QDBusPendingCallWatcher] = set()
        self._closed = False

    def call(
        self,
        path: str,
        interface: str,
        member: str,
        args: list,
        on_reply: ReplyHandler,
        on_error: ErrorHandler,
        service: str = SYSTEMD,
        signature: str = "",  # QtDBus infers types; only lists of str and UInt need help
    ) -> None:
        message = QDBusMessage.createMethodCall(service, path, interface, member)
        message.setArguments([_marshal(arg) for arg in args])
        message.setInteractiveAuthorizationAllowed(self._interactive)
        watcher = QDBusPendingCallWatcher(self._bus.asyncCall(message, self._timeout), self)
        self._pending.add(watcher)

        def finished(done: QDBusPendingCallWatcher) -> None:
            self._pending.discard(done)
            done.deleteLater()
            if self._closed:
                return
            reply = QDBusPendingReply(done)
            if reply.isError():
                on_error(reply.error().name(), reply.error().message())
            else:
                on_reply(reply.reply().arguments())

        watcher.finished.connect(finished)

    def subscribe(
        self, path: str, interface: str, member: str, handler: SignalHandler, service: str = SYSTEMD
    ) -> None:
        receiver = _Receiver(handler, self)
        if not self._bus.connect(service, path, interface, member, receiver.on_message):
            raise RuntimeError(f"cannot subscribe to {interface}.{member}")

    def close(self) -> None:
        """Receivers die with this object, which disconnects them from the bus."""
        self._closed = True
        try:
            self.deleteLater()
        except RuntimeError:
            pass  # already destroyed by Qt while the application shuts down


def _marshal(value: object) -> object:
    """A Python list of str would be sent as 'av' (systemd wants 'as'); UInt becomes uint32."""
    if isinstance(value, UInt):
        return QDBusArgument(int(value), QMetaType.Type.UInt.value)
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return QDBusArgument(value, QMetaType.Type.QStringList.value)
    return value


class QtRuntime(QObject):
    """Implements ``unitdeck.backend.base.Runtime`` on top of Qt."""

    def transport(self, bus: str, interactive: bool = False) -> QtDBusTransport:
        connection = (
            QDBusConnection.systemBus() if bus == "system" else QDBusConnection.sessionBus()
        )
        return QtDBusTransport(connection, interactive=interactive)

    def schedule(self, delay_ms: int, callback: Callable[[], None]) -> None:
        QTimer.singleShot(delay_ms, callback)

    def run(self, argv: list[str], stdin: str | None, on_done: ProcessDone) -> None:
        proc = QProcess(self)

        def finished(code: int, _status: object) -> None:
            out = bytes(proc.readAllStandardOutput()).decode("utf-8", "replace")
            err = bytes(proc.readAllStandardError()).decode("utf-8", "replace")
            proc.deleteLater()
            on_done(code, out, err)

        proc.finished.connect(finished)
        proc.start(argv[0], argv[1:])
        if stdin is not None:
            proc.write(stdin.encode("utf-8"))
        proc.closeWriteChannel()

    def stream(
        self,
        argv: list[str],
        on_line: Callable[[bytes], None],
        on_exit: Callable[[int, str], None],
    ) -> Callable[[], None]:
        proc = QProcess(self)
        buffer = bytearray()

        def read() -> None:
            buffer.extend(bytes(proc.readAllStandardOutput()))
            while (cut := buffer.find(b"\n")) >= 0:
                line = bytes(buffer[:cut])
                del buffer[: cut + 1]
                on_line(line)

        def finished(code: int, _status: object) -> None:
            read()
            err = bytes(proc.readAllStandardError()).decode("utf-8", "replace").strip()
            proc.deleteLater()
            on_exit(code, err)

        def stop() -> None:
            if proc.state() != QProcess.ProcessState.NotRunning:
                proc.terminate()
                if not proc.waitForFinished(1000):
                    proc.kill()

        proc.readyReadStandardOutput.connect(read)
        proc.finished.connect(finished)
        proc.start(argv[0], argv[1:])
        return stop
