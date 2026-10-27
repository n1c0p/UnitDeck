# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Nicola Palmieri (n1c0p)
"""The terminal application: one tab per scope with the unit table, filters and actions."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any

from rich.markup import escape
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import DataTable, Footer, Header, Input, Static, TabbedContent, TabPane

from unitdeck import __version__
from unitdeck.backend.base import Runtime, Scope, SystemdBackend, Unit
from unitdeck.backend.systemd import SystemBackend, UserBackend
from unitdeck.i18n import tr
from unitdeck.messages import ACTION_LABELS, AUTH_ERRORS, readable
from unitdeck.model import FILTER_LABELS, StateFilter
from unitdeck.tui.logs import LogScreen
from unitdeck.tui.polkit import TtyAgent, graphical_session

STATE_STYLES = {"active": "green", "failed": "bold red"}
COLUMNS = ("Name", "Description", "Load", "State", "Startup")


def state_text(unit: Unit, busy: bool) -> str:
    text = f"{unit.active_state} ({unit.sub_state})" if unit.loaded else "inactive"
    if busy:
        return f"[yellow]… {escape(text)}[/]"
    style = STATE_STYLES.get(unit.active_state, "dim")
    return f"[{style}]{escape(text)}[/]"


def matches(unit: Unit, text: str, state: StateFilter, own_dir: str) -> bool:
    if text and text not in unit.name.lower() and text not in unit.description.lower():
        return False
    match state:
        case StateFilter.ACTIVE:
            return unit.active_state not in ("inactive", "failed")
        case StateFilter.INACTIVE:
            return unit.active_state == "inactive"
        case StateFilter.FAILED:
            return unit.active_state == "failed"
        case StateFilter.MINE:
            return unit.fragment_path.startswith(own_dir.rstrip("/") + "/")
    return True


class UnitPane(Vertical):
    """Search field, filter label and the table of one backend."""

    DEFAULT_CSS = """
    UnitPane > Horizontal { height: 3; }
    UnitPane > Horizontal > Input { width: 1fr; }
    UnitPane > Horizontal > #filter { width: auto; padding: 1 2; }
    UnitPane > DataTable { height: 1fr; }
    """

    def __init__(self, backend: SystemdBackend) -> None:
        super().__init__()
        self.backend = backend
        self.text = ""
        self.state = StateFilter.ALL
        self._rows: dict[str, Unit] = {}

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield Input(placeholder=tr("Search by name or description…"))
            yield Static(id="filter")
        table = DataTable(cursor_type="row", zebra_stripes=True)
        yield table

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        for column in COLUMNS:
            table.add_column(tr(column), key=column)
        self.query_one("#filter", Static).update(self._filter_label())
        self.backend.units_changed.connect(self.rebuild)
        self.backend.unit_updated.connect(self.update_row)
        self.backend.busy_changed.connect(lambda name, _busy: self.update_row(name))
        self.backend.refresh()

    # ---- table ------------------------------------------------------------------------------

    def _cells(self, unit: Unit) -> list[str]:
        return [
            escape(unit.name),
            escape(unit.description),
            unit.load_state or tr("not loaded"),
            state_text(unit, unit.name in self.backend.busy),
            unit.unit_file_state or "–",
        ]

    def rebuild(self) -> None:
        table = self.query_one(DataTable)
        selected = self.selected_name()
        table.clear()
        self._rows = {}
        for name in sorted(self.backend.units):
            unit = self.backend.units[name]
            if matches(unit, self.text, self.state, self.backend.own_dir):
                self._rows[name] = unit
                table.add_row(*self._cells(unit), key=name)
        if selected in self._rows:
            table.move_cursor(row=table.get_row_index(selected))

    def update_row(self, name: str) -> None:
        unit = self.backend.units.get(name)
        if unit is None or name not in self._rows:
            return
        table = self.query_one(DataTable)
        for column, value in zip(COLUMNS, self._cells(unit), strict=True):
            table.update_cell(name, column, value)

    def selected_name(self) -> str | None:
        table = self.query_one(DataTable)
        if table.row_count == 0 or table.cursor_row < 0:
            return None
        try:
            return str(table.coordinate_to_cell_key((table.cursor_row, 0)).row_key.value)
        except Exception:  # noqa: BLE001 - no row under the cursor
            return None

    def selected_unit(self) -> Unit | None:
        name = self.selected_name()
        return self.backend.units.get(name) if name else None

    # ---- filters ----------------------------------------------------------------------------

    def on_input_changed(self, event: Input.Changed) -> None:
        self.text = event.value.strip().lower()
        self.rebuild()

    def on_input_submitted(self, _event: Input.Submitted) -> None:
        self.query_one(DataTable).focus()

    def cycle_filter(self) -> None:
        states = list(StateFilter)
        self.state = states[(states.index(self.state) + 1) % len(states)]
        self.query_one("#filter", Static).update(self._filter_label())
        self.rebuild()

    def _filter_label(self) -> str:
        return f"{tr('Filter')}: {tr(FILTER_LABELS[self.state])}"


class UnitDeckApp(App[None]):
    TITLE = "UnitDeck"
    SUB_TITLE = __version__
    CSS = """
    #status { dock: bottom; height: 1; padding: 0 1; background: $surface; color: $text-muted; }
    """
    BINDINGS = [
        Binding("s", "unit('start')", "Start"),
        Binding("x", "unit('stop')", "Stop"),
        Binding("r", "unit('restart')", "Restart"),
        Binding("e", "toggle_enable", "Enable/Disable"),
        Binding("m", "toggle_mask", "Mask/Unmask"),
        Binding("l", "logs", "Logs"),
        Binding("d", "daemon_reload", "daemon-reload"),
        Binding("slash", "focus_search", "Search", key_display="/"),
        Binding("f", "cycle_filter", "Filter"),
        Binding("f5", "refresh", "Refresh"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self, runtime_factory: Callable[[], Any] | None = None) -> None:
        super().__init__()
        self._runtime_factory = runtime_factory
        self._runtime: Runtime | None = None
        self._backends: list[SystemdBackend] = []
        self._tty_agent = not graphical_session()

    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent(id="scopes"):
            with TabPane(tr("System services"), id="system"):
                yield Static(tr("Connecting…"), id="placeholder-system")
            with TabPane(tr("User services"), id="user"):
                yield Static(tr("Connecting…"), id="placeholder-user")
        yield Static(tr("Ready"), id="status")
        yield Footer()

    async def on_mount(self) -> None:
        if self._runtime_factory is not None:
            self._runtime = self._runtime_factory()
        else:
            from unitdeck.backend.asyncio_runtime import AsyncioRuntime

            runtime = AsyncioRuntime()
            await runtime.connect()
            self._runtime = runtime
        for scope, backend_class in ((Scope.SYSTEM, SystemBackend), (Scope.USER, UserBackend)):
            backend = backend_class(self._runtime)
            backend.operation_finished.connect(self._on_finished)
            if backend.writer is not None:
                backend.writer.finished.connect(
                    lambda op, ok, detail: self._on_finished("", op, ok, detail)
                )
            self._backends.append(backend)
            pane = self.query_one(f"#{scope.value}", TabPane)
            await pane.query_one(f"#placeholder-{scope.value}").remove()
            await pane.mount(UnitPane(backend))

    # ---- helpers ----------------------------------------------------------------------------

    @property
    def pane(self) -> UnitPane | None:
        active = self.query_one("#scopes", TabbedContent).active_pane
        panes = active.query(UnitPane) if active is not None else []
        return panes.first() if panes else None

    def status(self, text: str) -> None:
        self.query_one("#status", Static).update(escape(text))

    def _on_finished(self, name: str, action: str, ok: bool, detail: str) -> None:
        label = tr(ACTION_LABELS.get(action, action))
        target = f" {name}" if name else ""
        if ok:
            self.status(
                tr("{action} {unit}: done").format(action=label, unit=name).replace("  ", " ")
            )
            return
        reason = readable(detail)
        self.status(f"{label}{target}: {reason}")
        if action not in ("refresh", "details") and detail.partition(": ")[0] not in AUTH_ERRORS:
            self.notify(f"{label}{target}: {reason}", severity="error", timeout=8)

    async def _run(self, backend: SystemdBackend, action: str, unit: Unit) -> None:
        if not unit.can(action) or unit.name in backend.busy:
            return
        self.status(tr("{action} {unit}…").format(action=tr(ACTION_LABELS[action]), unit=unit.name))
        if backend.scope is Scope.SYSTEM and self._tty_agent:
            # No graphical agent: leave the screen to pkttyagent until systemd answered.
            done: asyncio.Future[None] = asyncio.get_running_loop().create_future()

            def finished(name: str, finished_action: str, _ok: bool, _detail: str) -> None:
                if name == unit.name and finished_action == action and not done.done():
                    done.set_result(None)

            backend.operation_finished.connect(finished)
            try:
                with self.suspend(), TtyAgent():
                    backend.run(action, unit.name)
                    await asyncio.wait_for(done, 600)
            except TimeoutError:
                self.status(
                    tr("{action} {unit}: {reason}").format(
                        action=tr(ACTION_LABELS[action]), unit=unit.name, reason=tr("timed out")
                    )
                )
            finally:
                backend.operation_finished.disconnect(finished)
            return
        backend.run(action, unit.name)

    # ---- actions ----------------------------------------------------------------------------

    async def action_unit(self, action: str) -> None:
        pane = self.pane
        unit = pane.selected_unit() if pane else None
        if pane and unit:
            await self._run(pane.backend, action, unit)

    async def action_toggle_enable(self) -> None:
        pane = self.pane
        unit = pane.selected_unit() if pane else None
        if pane and unit:
            await self._run(pane.backend, "disable" if unit.can("disable") else "enable", unit)

    async def action_toggle_mask(self) -> None:
        pane = self.pane
        unit = pane.selected_unit() if pane else None
        if pane and unit:
            await self._run(pane.backend, "unmask" if unit.masked else "mask", unit)

    def action_logs(self) -> None:
        pane = self.pane
        unit = pane.selected_unit() if pane else None
        if pane and unit and self._runtime is not None:
            self.push_screen(LogScreen(unit.name, pane.backend.scope, self._runtime))

    def action_daemon_reload(self) -> None:
        if self.pane:
            self.pane.backend.daemon_reload()

    def action_focus_search(self) -> None:
        if self.pane:
            self.pane.query_one(Input).focus()

    def action_cycle_filter(self) -> None:
        if self.pane:
            self.pane.cycle_filter()

    def action_refresh(self) -> None:
        if self.pane:
            self.pane.backend.refresh()

    async def action_quit(self) -> None:
        for backend in self._backends:
            backend.close()
        close = getattr(self._runtime, "close", None)
        if close is not None:
            close()
        self.exit()
