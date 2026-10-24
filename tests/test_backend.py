# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Nicola Palmieri (n1c0p)
import pytest
from fake_transport import DBusError, FakeTransport

from unitdeck.backend.base import ACTIONS, Scope, Unit, own_unit_dir
from unitdeck.backend.systemd import UNIT_IFACE, QtDBusBackend, template_of

UNIT_PATH = "/org/freedesktop/systemd1/unit/web_2eservice"
LIST_UNITS = [
    ("web.service", "Web", "loaded", "active", "running", "", UNIT_PATH, 0, "", "/"),
    ("job@one.service", "Job one", "loaded", "inactive", "dead", "", "/u/job", 0, "", "/"),
    ("home.mount", "Home", "loaded", "active", "mounted", "", "/u/home", 0, "", "/"),
]
LIST_UNIT_FILES = [
    ("/usr/lib/systemd/user/web.service", "enabled"),
    ("/usr/lib/systemd/user/job@.service", "static"),
    ("/home/me/.config/systemd/user/mine.service", "disabled"),
    ("/usr/lib/systemd/user/drive.mount", "static"),
]


def make_backend(replies=None):
    transport = FakeTransport({"ListUnits": [LIST_UNITS], "ListUnitFiles": [LIST_UNIT_FILES]})
    transport.replies.update(replies or {})
    backend = QtDBusBackend(Scope.USER, transport)
    backend.own_dir = "/home/me/.config/systemd/user"
    return backend, transport


def test_own_unit_dir(monkeypatch):
    assert own_unit_dir(Scope.SYSTEM) == "/etc/systemd/system"
    monkeypatch.setenv("XDG_CONFIG_HOME", "/tmp/cfg")
    assert own_unit_dir(Scope.USER) == "/tmp/cfg/systemd/user"


def test_system_scope_backend_marks_etc_units_as_mine():
    transport = FakeTransport(
        {"ListUnits": [[]], "ListUnitFiles": [[("/etc/systemd/system/mine.service", "enabled")]]}
    )
    backend = QtDBusBackend(Scope.SYSTEM, transport)
    backend.refresh()
    assert backend.units["mine.service"].fragment_path.startswith(backend.own_dir)


def test_template_of():
    assert template_of("job@one.service") == "job@.service"
    assert template_of("web.service") == ""


def test_subscribes_on_startup():
    backend, transport = make_backend()
    assert transport.members() == ["Subscribe"]
    assert {
        "UnitNew",
        "UnitRemoved",
        "JobRemoved",
        "PropertiesChanged",
    } <= transport.handlers.keys()


def test_refresh_merges_units_and_unit_files():
    backend, transport = make_backend()
    seen = []
    backend.units_changed.connect(lambda: seen.append(True))
    backend.refresh()
    assert seen
    assert set(backend.units) == {"web.service", "job@one.service", "mine.service"}
    web = backend.units["web.service"]
    assert web.loaded and web.running and web.unit_file_state == "enabled"
    assert web.fragment_path == "/usr/lib/systemd/user/web.service"
    instance = backend.units["job@one.service"]
    assert instance.unit_file_state == "static"  # taken from the template file
    mine = backend.units["mine.service"]
    assert not mine.loaded and mine.load_state == "" and mine.unit_file_state == "disabled"
    assert mine.fragment_path.startswith(backend.own_dir)


def test_properties_changed_updates_unit_in_place():
    backend, transport = make_backend()
    backend.refresh()
    updated = []
    backend.unit_updated.connect(updated.append)
    transport.emit(
        "PropertiesChanged",
        UNIT_PATH,
        [UNIT_IFACE, {"ActiveState": "failed", "SubState": "failed"}, []],
    )
    assert updated == ["web.service"]
    assert backend.units["web.service"].active_state == "failed"
    transport.emit("PropertiesChanged", "/unknown", [UNIT_IFACE, {"ActiveState": "active"}, []])
    transport.emit(
        "PropertiesChanged", UNIT_PATH, ["org.freedesktop.systemd1.Service", {"MainPID": 1}, []]
    )
    assert updated == ["web.service"]


def test_start_tracks_job_until_removed():
    backend, transport = make_backend({"StartUnit": ["/org/freedesktop/systemd1/job/7"]})
    backend.refresh()
    results = []
    backend.operation_finished.connect(lambda *args: results.append(args))
    backend.run("start", "mine.service")
    assert transport.calls[-1][2:] == ("StartUnit", ["mine.service", "replace"])
    assert "mine.service" in backend.busy and results == []
    transport.emit(
        "JobRemoved",
        "/org/freedesktop/systemd1",
        [7, "/org/freedesktop/systemd1/job/7", "mine.service", "done"],
    )
    assert backend.busy == set()
    assert results == [("mine.service", "start", True, "done")]


def test_failed_job_and_dbus_error_are_reported():
    backend, transport = make_backend(
        {
            "RestartUnit": ["/j/1"],
            "Get": ["start-limit-hit"],
            "StopUnit": DBusError("org.freedesktop.systemd1.NoSuchUnit", "Unit x not found."),
        }
    )
    backend.refresh()
    results = []
    backend.operation_finished.connect(lambda *args: results.append(args))
    backend.run("restart", "web.service")
    transport.emit("JobRemoved", "/org/freedesktop/systemd1", [1, "/j/1", "web.service", "failed"])
    backend.run("stop", "x.service")
    assert results == [
        ("web.service", "restart", False, "failed (start-limit-hit)"),
        ("x.service", "stop", False, "org.freedesktop.systemd1.NoSuchUnit: Unit x not found."),
    ]
    assert backend.busy == set()


def test_enable_passes_name_list_then_reloads():
    backend, transport = make_backend()
    results = []
    backend.operation_finished.connect(lambda *args: results.append(args))
    backend.run("enable", "mine.service")
    assert transport.calls[-2][2:] == ("EnableUnitFiles", [["mine.service"], False, False])
    assert transport.calls[-1][2] == "Reload"
    assert results == [("mine.service", "enable", True, "")]
    backend.run("mask", "mine.service")
    assert transport.calls[-2][2:] == ("MaskUnitFiles", [["mine.service"], False, False])


def test_fetch_details_reads_can_reload_and_drop_ins():
    props = {
        "CanReload": True,
        "DropInPaths": ["/etc/x.d/override.conf"],
        "FragmentPath": "/usr/lib/x",
    }
    backend, transport = make_backend({"GetAll": [props]})
    backend.refresh()
    backend.fetch_details("mine.service")  # not loaded: no call
    assert transport.members().count("GetAll") == 0
    backend.fetch_details("web.service")
    assert transport.calls[-1][:3] == (UNIT_PATH, "org.freedesktop.DBus.Properties", "GetAll")
    web = backend.units["web.service"]
    assert web.can_reload is True and web.drop_in_paths == ["/etc/x.d/override.conf"]
    assert web.can("reload")
    backend.refresh()  # details survive a refresh of the same loaded unit
    assert backend.units["web.service"].can_reload is True


def test_reset_failed_is_a_plain_call():
    backend, transport = make_backend()
    results = []
    backend.operation_finished.connect(lambda *args: results.append(args))
    backend.run("reset-failed", "web.service")
    assert transport.calls[-1][2:] == ("ResetFailedUnit", ["web.service"])
    assert results == [("web.service", "reset-failed", True, "")] and backend.busy == set()


def test_unknown_action_is_rejected():
    backend, _ = make_backend()
    with pytest.raises(ValueError):
        backend.run("explode", "web.service")


@pytest.mark.parametrize(
    ("unit", "allowed"),
    [
        (
            Unit("a.service", active_state="active", unit_file_state="enabled"),
            {"stop", "restart", "disable", "mask"},
        ),
        (Unit("b.service", unit_file_state="disabled"), {"start", "enable", "mask"}),
        (Unit("c.service", load_state="masked", unit_file_state="masked"), {"unmask"}),
        (
            Unit("e.service", active_state="failed", unit_file_state="enabled"),
            {"start", "disable", "mask", "reset-failed"},
        ),
        (Unit("d.service", active_state="active", can_reload=True), {"stop", "restart", "reload"}),
    ],
)
def test_unit_can(unit, allowed):
    assert {a for a in ACTIONS if unit.can(a)} == allowed
