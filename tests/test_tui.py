# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Nicola Palmieri (n1c0p)
"""The terminal application driven headless by Textual's pilot on the fake runtime."""

import pytest
from fake_transport import FakeRuntime, FakeTransport
from textual.widgets import DataTable

from unitdeck.backend.base import Unit
from unitdeck.model import StateFilter
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


def make_runtime():
    transport = FakeTransport(
        {
            "ListUnits": [UNITS],
            "ListUnitFiles": [FILES],
            "StartUnit": ["/j/1"],
            "StopUnit": ["/j/2"],
        }
    )
    return FakeRuntime(transport)


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
    app = UnitDeckApp(runtime_factory=lambda: runtime)
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
