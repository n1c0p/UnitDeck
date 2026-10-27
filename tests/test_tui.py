# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Nicola Palmieri (n1c0p)
"""The terminal application driven headless by Textual's pilot on the fake runtime."""

import pytest
from fake_transport import FakeRuntime, FakeTransport
from textual.widgets import DataTable

from unitdeck.backend.base import Unit
from unitdeck.filters import StateFilter
from unitdeck.tui.app import UnitDeckApp, UnitPane, matches, state_text

UNITS = [
    ("web.service", "Web server", "loaded", "active", "running", "", "/u/web", 0, "", "/"),
    ("db.service", "Database", "loaded", "inactive", "dead", "", "/u/db", 0, "", "/"),
    ("bad.service", "Broken", "loaded", "failed", "failed", "", "/u/bad", 0, "", "/"),
]
FILES = [
    ("/usr/lib/systemd/user/web.service", "enabled"),
    ("/usr/lib/systemd/user/db.service", "disabled"),
]


def make_runtime(own_dir="/own"):
    transport = FakeTransport(
        {
            "ListUnits": [UNITS],
            "ListUnitFiles": [FILES],
            "StartUnit": ["/j/1"],
            "StopUnit": ["/j/2"],
            "GetUser": ["/org/freedesktop/login1/user/_1000"],
            "Get": [False],
            "GetAll": [{}],
        }
    )
    runtime = FakeRuntime(transport)
    runtime.own_dir = own_dir
    return runtime


def make_app(runtime):
    app = UnitDeckApp(runtime_factory=lambda: runtime)
    app._tty_agent = False  # the pkttyagent flow needs a real terminal; not under test here
    return app


def test_matches_and_state_text():
    unit = Unit("a.service", "Alpha", "loaded", "active", "running", object_path="/u/a")
    assert matches(unit, "alpha", StateFilter.ALL, "/own")
    assert not matches(unit, "zzz", StateFilter.ALL, "/own")
    assert matches(unit, "", StateFilter.ACTIVE, "/own") and not matches(
        unit, "", StateFilter.FAILED, "/own"
    )
    assert "green" in state_text(unit, False) and "…" in state_text(unit, True)
    assert state_text(Unit("b.service"), False) == "[dim]inactive[/]"


@pytest.mark.asyncio
async def test_app_lists_filters_and_runs_actions():
    runtime = make_runtime()
    app = make_app(runtime)
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        panes = app.query(UnitPane)
        assert len(panes) == 2
        table = panes.first().query_one(DataTable)
        assert table.row_count == 3
        # the system tab is active first; its backend got Subscribe + the two lists
        members = runtime._transport.members()
        assert members.count("ListUnits") >= 2 and "Subscribe" in members
        # filter: failed only
        await pilot.press("f", "f", "f")  # all -> active -> inactive -> failed
        await pilot.pause()
        assert app.pane.state is StateFilter.FAILED and app.pane.query_one(DataTable).row_count == 1
        await pilot.press("f", "f")  # mine -> all
        await pilot.pause()
        assert app.pane.query_one(DataTable).row_count == 3
        # search
        await pilot.press("slash")
        await pilot.press(*"web")
        await pilot.press("enter")
        await pilot.pause()
        assert app.pane.query_one(DataTable).row_count == 1
        assert app.pane.selected_name() == "web.service"
        # stop the selected (active) unit: StopUnit goes out, the row shows busy
        await pilot.press("x")
        await pilot.pause()
        assert runtime._transport.calls[-1][2:] == ("StopUnit", ["web.service", "replace"])
        assert "web.service" in app.pane.backend.busy
        # both backends share the fake transport, so deliver the signal to the active one
        app.pane.backend._on_job_removed(
            "/org/freedesktop/systemd1", [2, "/j/2", "web.service", "done"]
        )
        await pilot.pause()
        assert "web.service" not in app.pane.backend.busy
        assert "done" in str(app.query_one("#status").content)
        # start is refused on an active unit: no new call
        before = len(runtime._transport.calls)
        await pilot.press("s")
        await pilot.pause()
        assert len(runtime._transport.calls) == before
        await pilot.press("q")


@pytest.mark.asyncio
async def test_user_tab_linger_editor_and_new_service(tmp_path, monkeypatch):
    from textual.widgets import TextArea

    from unitdeck.backend import base
    from unitdeck.tui.screens import EditScreen, NewServiceScreen

    monkeypatch.setattr(base, "own_unit_dir", lambda scope: str(tmp_path))
    mine = tmp_path / "mine.service"
    mine.write_text("[Unit]\nDescription=Mine\n\n[Service]\nExecStart=/bin/true\n")
    units = UNITS + [
        ("mine.service", "Mine", "loaded", "inactive", "dead", "", "/u/mine", 0, "", "/")
    ]
    files = FILES + [(str(mine), "disabled")]
    runtime = make_runtime(str(tmp_path))
    runtime._transport.replies["ListUnits"] = [units]
    runtime._transport.replies["ListUnitFiles"] = [files]
    transport = runtime._transport
    app = make_app(runtime)
    async with app.run_test(size=(120, 45)) as pilot:
        await pilot.pause()
        # user tab: linger label read from logind, toggled with g
        app.query_one("#scopes").active = "user"
        await pilot.pause()
        pane = app.pane
        assert pane.backend.scope.value == "user"
        assert "Linger" in str(pane.query_one("#linger").content)
        await pilot.press("g")
        await pilot.pause()
        assert (
            transport.calls[-1][2:] == ("SetUserLinger", [1000, True, True])
            or transport.calls[-1][2] == "Get"
        )
        assert any(c[2] == "SetUserLinger" for c in transport.calls)
        # editor on the user-created unit: direct edit, saved through UserWriter
        await pilot.press("slash")
        await pilot.press(*"mine")
        await pilot.press("enter")
        await pilot.pause()
        assert pane.selected_name() == "mine.service"
        await pilot.press("ctrl+e")
        await pilot.pause()
        assert isinstance(app.screen, EditScreen)
        editor = app.screen.query_one("#editor", TextArea)
        assert "ExecStart=/bin/true" in editor.text
        editor.load_text(editor.text + "Nice=5\n")
        await pilot.press("ctrl+s")
        await pilot.pause()
        await pilot.pause()
        assert "Nice=5" in mine.read_text() and (tmp_path / "mine.service.bak").exists()
        assert not isinstance(app.screen, EditScreen)
        # new service from the first template
        await pilot.press("n")
        await pilot.pause()
        assert isinstance(app.screen, NewServiceScreen)
        screen = app.screen
        screen.query_one("#name").value = "test-new"
        await pilot.pause()
        screen.query_one("#f-EXEC_START").value = "/bin/sleep 1"
        await pilot.pause()
        screen._create()
        await pilot.pause()
        await pilot.pause()
        created = tmp_path / "test-new.service"
        assert created.exists() and "ExecStart=/bin/sleep 1" in created.read_text()
        assert not isinstance(app.screen, NewServiceScreen)
        members = [c[2] for c in transport.calls[-6:]]
        assert "EnableUnitFiles" in members and "StartUnit" in members
        await pilot.press("q")
