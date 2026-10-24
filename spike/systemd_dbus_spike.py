# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Nicola (n1c0p)
"""Spike: prove that PyQt6.QtDBus is enough for UnitDeck.

1. ListUnits on the system bus, asynchronously, with complex return types.
2. StartUnit on the system bus with interactive authorization, so that
   systemd delegates to polkit and the desktop authentication dialog appears.

Usage:
    python spike/systemd_dbus_spike.py             # list only
    python spike/systemd_dbus_spike.py UNIT        # list, then StartUnit(UNIT)

Pick a unit that is already active (e.g. dbus.service): starting it is a
no-op for systemd, but polkit is consulted before the job is created, so the
dialog appears anyway. Cancel it to see the denied path handled.
"""

import sys
import time

from PyQt6.QtCore import QCoreApplication, QTimer
from PyQt6.QtDBus import (
    QDBusConnection,
    QDBusMessage,
    QDBusPendingCallWatcher,
    QDBusPendingReply,
)

SERVICE = "org.freedesktop.systemd1"
PATH = "/org/freedesktop/systemd1"
MANAGER = "org.freedesktop.systemd1.Manager"
POLKIT_TIMEOUT_MS = 10 * 60 * 1000  # QtDBus default is 25 s: too short for a dialog

app = QCoreApplication(sys.argv)
bus = QDBusConnection.systemBus()
t0 = time.monotonic()
watchers = []  # keep references alive until finished


def log(msg: str) -> None:
    print(f"[{time.monotonic() - t0:6.2f}s] {msg}", flush=True)


def call_async(member: str, *args, timeout: int = -1, on_done) -> None:
    msg = QDBusMessage.createMethodCall(SERVICE, PATH, MANAGER, member)
    msg.setArguments(list(args))
    msg.setInteractiveAuthorizationAllowed(True)
    watcher = QDBusPendingCallWatcher(bus.asyncCall(msg, timeout))
    watchers.append(watcher)
    watcher.finished.connect(lambda w: on_done(QDBusPendingReply(w)))


def on_list(reply: QDBusPendingReply) -> None:
    if reply.isError():
        log(f"ListUnits FAILED: {reply.error().name()}: {reply.error().message()}")
        return app.exit(1)
    services = sorted(u for u in reply.argumentAt(0) if u[0].endswith(".service"))
    log(f"ListUnits OK: {len(reply.argumentAt(0))} units, {len(services)} .service")
    for name, desc, load, active, sub, *_ in services[:8]:
        log(f"  {name:40} {load:8} {active:8} {sub:10} {desc}")
    if len(sys.argv) < 2:
        return app.quit()
    unit = sys.argv[1]
    log(f"StartUnit({unit}) with interactive authorization; waiting for polkit...")
    call_async("StartUnit", unit, "replace", timeout=POLKIT_TIMEOUT_MS, on_done=on_start)


def on_start(reply: QDBusPendingReply) -> None:
    if reply.isError():
        log(f"StartUnit DENIED/FAILED: {reply.error().name()}: {reply.error().message()}")
        return app.exit(2)
    log(f"StartUnit OK, job: {reply.argumentAt(0)}")
    app.quit()


# Heartbeat: proves the event loop keeps running while D-Bus calls are pending.
tick = QTimer()
tick.timeout.connect(lambda: log("event loop alive"))
tick.start(1000)

log(f"system bus connected: {bus.isConnected()}")
call_async("ListUnits", on_done=on_list)
sys.exit(app.exec())
