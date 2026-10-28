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
    from textual.widgets import Input, TextArea

    from unitdeck.backend import base
    from unitdeck.tui.screens import EditScreen, NewServiceScreen
    from unitdeck.tui.service_editor import Row, ServiceEditor

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
        screen._create()  # refused: ExecStart= is still empty
        await pilot.pause()
        assert "ExecStart" in str(screen.query_one("#output").content)
        assert not (tmp_path / "test-new.service").exists()
        exec_start = next(r for r in screen.query(Row) if r.directive.key == "ExecStart")
        exec_start.query_one(Input).value = "/bin/sleep 1"
        await pilot.pause()
        assert "Description=test-new" in screen.query_one(ServiceEditor).text
        screen._create()
        await pilot.pause()
        await pilot.pause()
        created = tmp_path / "test-new.service"
        assert created.exists() and "ExecStart=/bin/sleep 1" in created.read_text()
        assert not isinstance(app.screen, NewServiceScreen)
        members = [c[2] for c in transport.calls[-6:]]
        assert "EnableUnitFiles" in members and "StartUnit" in members
        await pilot.press("q")


@pytest.mark.asyncio
async def test_service_editor_builder(tmp_path, monkeypatch):
    from textual.widgets import Input, TextArea

    from unitdeck.backend import base
    from unitdeck.tui.screens import EditScreen
    from unitdeck.tui.service_editor import InfoScreen, Section, ServiceEditor

    monkeypatch.setattr(base, "own_unit_dir", lambda scope: str(tmp_path))
    mine = tmp_path / "mine.service"
    mine.write_text(
        "# my note\n[Unit]\nDescription=Mine\n\n[Service]\nType=simple\n"
        "ExecStart=/bin/true\nRestrat=always\n\n[Install]\nWantedBy=default.target\n"
    )
    units = UNITS + [
        ("mine.service", "Mine", "loaded", "inactive", "dead", "", "/u/mine", 0, "", "/")
    ]
    runtime = make_runtime(str(tmp_path))
    runtime._transport.replies["ListUnits"] = [units]
    runtime._transport.replies["ListUnitFiles"] = [FILES + [(str(mine), "disabled")]]
    app = make_app(runtime)
    async with app.run_test(size=(120, 45)) as pilot:
        await pilot.pause()
        app.query_one("#scopes").active = "user"
        await pilot.pause()
        await pilot.press("slash", *"mine", "enter")
        await pilot.pause()
        await pilot.press("ctrl+e")
        await pilot.pause()
        assert isinstance(app.screen, EditScreen)
        editor = app.screen.query_one(ServiceEditor)
        service = next(s for s in editor.query(Section) if s.section == "Service")

        def keys():
            return [row.directive.key for row in service.row_list()]

        assert keys() == ["Type", "ExecStart", "Restrat"]
        assert service.row_list()[2].problem.endswith("Did you mean Restart?")

        # pick, then Add: a row with a typed field, written to the text at once
        service._picker.value = "RestartSec"
        await pilot.pause()
        assert keys()[-1] == "Restrat"  # picking alone adds nothing
        service._add.press()
        await pilot.pause()
        row = service.row_list()[-1]
        assert row.directive.key == "RestartSec" and row.has_focus_within
        row.query_one(Input).value = "5s"
        await pilot.pause()
        assert "Restrat=always\nRestartSec=5s\n" in editor.text
        assert editor.text.startswith("# my note\n[Unit]")  # untouched lines and comments stay

        # keyboard: move up, info, remove
        await pilot.press("ctrl+up")
        await pilot.pause()
        assert keys() == ["Type", "ExecStart", "RestartSec", "Restrat"]
        assert "ExecStart=/bin/true\nRestartSec=5s\nRestrat" in editor.text
        await pilot.press("f1")
        await pilot.pause()
        assert isinstance(app.screen, InfoScreen)
        await pilot.press("escape")
        await pilot.pause()
        service.row_list()[3].focus_field()
        await pilot.press("f8")
        await pilot.pause()
        assert "Restrat" not in keys() and "Restrat" not in editor.text

        # Text tab -> form when going back to Builder
        await pilot.press("f3")
        await pilot.pause()
        text_area = editor.query_one("#editor", TextArea)
        text_area.load_text(text_area.text.replace("Type=simple", "Type=oneshot\nUser=nobody"))
        await pilot.press("f2")
        await pilot.pause()
        assert keys()[:3] == ["Type", "User", "ExecStart"]
        assert service.row_list()[0].value() == "oneshot"

        # save writes the text
        await pilot.press("ctrl+s")
        await pilot.pause()
        await pilot.pause()
        assert "User=nobody" in mine.read_text() and "# my note" in mine.read_text()

        # package unit: drop-in; a directive of a missing section creates the section
        await pilot.press("slash", *(["backspace"] * 4), *"web", "enter")
        await pilot.pause()
        await pilot.press("ctrl+e")
        await pilot.pause()
        editor = app.screen.query_one(ServiceEditor)
        assert editor.text.endswith("[Service]\n")
        unit_section = next(s for s in editor.query(Section) if s.section == "Unit")
        unit_section._picker.value = "Description"
        unit_section._add.press()
        await pilot.pause()
        unit_section.row_list()[0].query_one(Input).value = "Web"
        await pilot.pause()
        assert editor.text.endswith("\n[Unit]\nDescription=Web\n\n[Service]\n")
        assert editor.text.startswith("# Drop-in for web.service")
        await pilot.press("escape")
        await pilot.press("q")
