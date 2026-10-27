# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Nicola Palmieri (n1c0p)
from fake_transport import DBusError, FakeTransport

from unitdeck.backend.base import UInt
from unitdeck.backend.linger import USER_IFACE, LingerControl


def test_linger_reads_state_and_follows_changes():
    transport = FakeTransport({"GetUser": ["/org/freedesktop/login1/user/_1000"], "Get": [False]})
    control = LingerControl(transport, uid=1000)
    states = []
    control.changed.connect(states.append)
    control.refresh()
    assert transport.calls[0][2:] == ("GetUser", [1000])
    assert isinstance(transport.calls[0][3][0], UInt)
    assert transport.signatures["GetUser"] == "u"
    assert transport.calls[-1][:3] == (
        "/org/freedesktop/login1/user/_1000",
        "org.freedesktop.DBus.Properties",
        "Get",
    )
    assert states == [False]
    transport.emit(
        "PropertiesChanged",
        "/org/freedesktop/login1/user/_1000",
        [USER_IFACE, {"Linger": True}, []],
    )
    assert states == [False, True]


def test_set_linger_passes_interactive_flag_and_reports_errors():
    transport = FakeTransport({"GetUser": ["/u"], "Get": [True], "SetUserLinger": []})
    control = LingerControl(transport, uid=7)
    states, errors = [], []
    control.changed.connect(states.append)
    control.failed.connect(errors.append)
    control.set_linger(True)
    assert transport.calls[0][2:] == ("SetUserLinger", [7, True, True])
    assert states == [True]  # re-read after the call
    transport.replies["SetUserLinger"] = DBusError("org.freedesktop.DBus.Error.AccessDenied", "no")
    control.set_linger(False)
    assert errors == ["org.freedesktop.DBus.Error.AccessDenied: no"]
