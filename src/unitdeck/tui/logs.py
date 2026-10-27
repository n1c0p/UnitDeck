# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Nicola Palmieri (n1c0p)
"""Journal screen: last lines of a unit, optional live follow."""

from __future__ import annotations

from rich.markup import escape
from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import ModalScreen
from textual.widgets import Footer, RichLog, Static

from unitdeck.backend.base import Runtime, Scope
from unitdeck.backend.journal import JournalReader
from unitdeck.i18n import tr

PRIORITY_STYLES = {0: "bold red", 1: "bold red", 2: "bold red", 3: "red", 4: "yellow"}
LINES = 300


class LogScreen(ModalScreen[None]):
    BINDINGS = [
        Binding("escape,q", "close", "Close"),
        Binding("f", "follow", "Follow"),
    ]
    DEFAULT_CSS = """
    LogScreen { align: center middle; }
    LogScreen > #title { dock: top; height: 1; background: $primary; color: $text; padding: 0 1; }
    LogScreen > RichLog { height: 1fr; }
    """

    def __init__(self, unit: str, scope: Scope, runtime: Runtime) -> None:
        super().__init__()
        self._unit = unit
        self._scope = scope
        self._reader = JournalReader(runtime)
        self._follow = False
        self._count = 0
        self._reader.entry.connect(self._on_entry)
        self._reader.finished.connect(self._on_finished)

    def compose(self) -> ComposeResult:
        yield Static(id="title")
        yield RichLog(highlight=False, markup=True, wrap=True)
        yield Footer()

    def on_mount(self) -> None:
        self._restart()

    def _restart(self) -> None:
        mode = tr("Follow (live)") if self._follow else tr("last {n} lines").format(n=LINES)
        self.query_one("#title", Static).update(
            f"{tr('Logs – {unit}').format(unit=self._unit)}  [{mode}]"
        )
        self.query_one(RichLog).clear()
        self._count = 0
        self._reader.start(self._unit, self._scope, LINES, 7, self._follow)

    def _on_entry(self, line: str, priority: int) -> None:
        self._count += 1
        style = PRIORITY_STYLES.get(priority)
        text = escape(line)
        self.query_one(RichLog).write(f"[{style}]{text}[/]" if style else text)

    def _on_finished(self, code: int, stderr: str) -> None:
        log = self.query_one(RichLog)
        if stderr:
            log.write(f"[italic]journalctl: {escape(stderr)}[/]")
        elif self._count == 0:
            log.write(f"[italic]{escape(tr('No journal entries for this unit.'))}[/]")

    def action_follow(self) -> None:
        self._follow = not self._follow
        self._restart()

    def action_close(self) -> None:
        self._reader.stop()
        self.dismiss()
