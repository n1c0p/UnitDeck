# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Nicola Palmieri (n1c0p)
from fake_transport import FakeRuntime, FakeTransport

from unitdeck.backend import unitfiles
from unitdeck.backend.base import Scope
from unitdeck.backend.systemd import DBusBackend
from unitdeck.backend.unitfiles import HelperWriter, UserWriter


def make(tmp_path, process_results=None):
    transport = FakeTransport()
    runtime = FakeRuntime(transport, process_results)
    backend = DBusBackend(Scope.USER, transport, runtime)
    backend.own_dir = str(tmp_path)
    return backend, transport, runtime


def test_user_writer_writes_then_reloads(tmp_path):
    backend, transport, _ = make(tmp_path)
    writer = UserWriter(backend)
    results = []
    writer.finished.connect(lambda *args: results.append(args))
    writer.write_unit("a.service", "[Unit]\n")
    assert (tmp_path / "a.service").read_text() == "[Unit]\n"
    assert transport.members()[-1] == "Reload" and results == [("save", True, "")]
    writer.delete_unit("missing.service")
    assert results[-1][0] == "delete" and results[-1][1] is False


def test_helper_writer_runs_pkexec_and_maps_exit_codes(tmp_path, monkeypatch):
    monkeypatch.setattr(unitfiles, "HELPER_PATH", str(tmp_path / "helper"))
    backend, _, runtime = make(tmp_path, [(0, "", ""), (126, "", "dismissed"), (1, "", "refused")])
    writer = HelperWriter(backend)
    results = []
    writer.finished.connect(lambda *args: results.append(args))
    writer.write_dropin("a.service", "x")
    assert results == [("save", False, f"{unitfiles.HELPER_MISSING}: {tmp_path / 'helper'}")]
    (tmp_path / "helper").write_text("")
    writer.write_dropin("a.service", "x")
    assert runtime.processes[-1] == (
        ["pkexec", str(tmp_path / "helper"), "write-dropin", "a.service", "--reload"],
        "x",
    )
    assert results[-1] == ("save", True, "")
    writer.delete_unit("a.service")
    assert results[-1][0] == "delete" and results[-1][2].startswith(
        "org.freedesktop.DBus.Error.AccessDenied"
    )
    writer.write_unit("a.service", "y")
    assert results[-1] == ("save", False, "refused")
