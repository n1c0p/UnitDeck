# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Nicola Palmieri (n1c0p)
"""Service editor for the terminal: a form builder ([Unit], [Service], [Install]) and the text.

Same rules as the desktop editor (gui/service_form.py), on the same shared code
(backend.unitparse, backend.directives): the text is the source of truth, every form change
rewrites it, text edits reach the form when going back to the Builder tab. No drag and drop in
a terminal: rows move with Ctrl+Up / Ctrl+Down.
"""

from __future__ import annotations

from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.content import Content
from textual.screen import ModalScreen
from textual.widget import Widget
from textual.widgets import (
    Button,
    Checkbox,
    Collapsible,
    Input,
    Label,
    Select,
    Static,
    TabbedContent,
    TabPane,
    TextArea,
)

from unitdeck.backend import directives, unitparse
from unitdeck.backend.directives import SECTIONS, Directive
from unitdeck.backend.unitparse import Entry
from unitdeck.i18n import tr

WIDE = 110  # columns from which the Builder tab shows the preview next to the form


def info_text(d: Directive) -> Content:
    """What the info dialog says about a directive. Built as Content, not markup: Textual
    markup would swallow "[Service]"."""
    if not d.info:
        return Content(tr("UnitDeck has no description for this directive.")).append(
            Content.styled(f"\n\nman {d.man}", "italic")
        )
    parts: list[Content | str] = [
        tr(d.info),
        "\n\n",
        Content.styled(tr("Example:"), "bold"),
        "\n",
        Content(f"[{d.section}]\n{d.key}={d.example}"),
    ]
    if d.choices:
        parts += ["\n\n", Content.styled(tr("Values:"), "bold"), " ", ", ".join(d.choices)]
    if d.repeatable:
        parts += ["\n\n", tr("Can be set more than once.")]
    parts += ["\n\n", Content.styled(f"man {d.man}", "italic")]
    return Content.assemble(*parts)


class InfoScreen(ModalScreen[None]):
    DEFAULT_CSS = """
    InfoScreen { align: center middle; }
    InfoScreen > Vertical { width: 76; max-width: 100%; height: auto; max-height: 90%;
                            border: thick $primary; padding: 1 2; }
    InfoScreen #title { text-style: bold; margin-bottom: 1; }
    InfoScreen Button { margin-top: 1; }
    """
    BINDINGS = [Binding("escape,enter,f1", "close", "Close")]

    def __init__(self, directive: Directive) -> None:
        super().__init__()
        self._directive = directive

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static(Content(f"{self._directive.key}="), id="title")
            with VerticalScroll():
                yield Static(info_text(self._directive))
            yield Button(tr("Close"), variant="primary", compact=True)

    def on_button_pressed(self) -> None:
        self.dismiss()

    def action_close(self) -> None:
        self.dismiss()


class Row(Horizontal):
    """One directive: name, typed field, info and remove buttons."""

    DEFAULT_CSS = """
    Row { height: auto; }
    Row > .name { width: 26; padding: 0 1; }
    Row > .name.warning { color: $warning; }
    Row > .field { width: 1fr; }
    Row > Button { min-width: 3; }
    """
    BINDINGS = [
        Binding("ctrl+up", "move(-1)", "Move up"),
        Binding("ctrl+down", "move(1)", "Move down"),
        Binding("f1", "info", "Info"),
        Binding("f8", "remove", "Remove"),
    ]

    def __init__(self, section: Section, directive: Directive, entry: Entry) -> None:
        super().__init__()
        self.section = section
        self.directive = directive
        self.entry = entry  # keeps lead comments and the original lines
        self.problem = ""
        self._name = Label(directive.key, classes="name")
        self._field = self._make_field(directive, entry.value)

    def compose(self) -> ComposeResult:
        yield self._name
        yield self._field
        yield Button("ⓘ", classes="info", compact=True, tooltip=tr("What is this directive for?"))
        yield Button("✕", classes="remove", compact=True, tooltip=tr("Remove this directive"))

    def on_mount(self) -> None:
        self.check()

    @staticmethod
    def _make_field(d: Directive, value: str) -> Widget:
        if d.kind == "enum" and directives.fits_widget(d, value):
            options = [(choice, choice) for choice in d.choices]
            return Select(options, value=value, allow_blank=False, compact=True, classes="field")
        if d.kind == "bool" and directives.fits_widget(d, value):
            checked = bool(directives.parse_bool(value))
            return Checkbox(tr("enabled"), checked, compact=True, classes="field")
        if "\n" in value:  # continuation lines: shown on one line, edited in the Text tab
            shown = value.replace("\\\n", " ").replace("\n", " ")
            tip = tr("Value split over several lines: edit it in the Text tab.")
            return Input(shown, disabled=True, tooltip=tip, compact=True, classes="field")
        return Input(value, placeholder=d.example, compact=True, classes="field")

    def value(self) -> str:
        field = self._field
        if isinstance(field, Select):
            return str(field.value)
        if isinstance(field, Checkbox):
            return directives.bool_value(field.value, self.entry.orig)
        if field.disabled:
            return self.entry.value
        return field.value.strip()

    def to_entry(self) -> Entry:
        e = self.entry
        return Entry(e.key, self.value(), e.lead, e.raw, e.orig)

    def focus_field(self) -> None:
        if not self._field.disabled:
            self._field.focus()

    def check(self) -> None:
        self.problem = directives.problem(self.directive, self.value())
        self._name.update(f"⚠ {self.directive.key}" if self.problem else self.directive.key)
        self._name.set_class(bool(self.problem), "warning")

    @on(Input.Changed)
    @on(Select.Changed)
    @on(Checkbox.Changed)
    def _changed(self, event) -> None:
        event.stop()
        self.check()
        self.section.editor.form_changed()
        focused = self.screen.focused
        if focused is not None and self in focused.ancestors_with_self:
            self.section.editor.show_hint(self)

    @on(Button.Pressed, ".info")
    def action_info(self) -> None:
        self.app.push_screen(InfoScreen(self.directive))

    @on(Button.Pressed, ".remove")
    async def action_remove(self) -> None:
        await self.section.remove_row(self)

    def action_move(self, delta: int) -> None:
        self.section.move_row(self, delta)


class Section(Collapsible):
    """Collapsible [Section]: its rows, then a directive picker with Info and Add."""

    DEFAULT_CSS = """
    Section { height: auto; padding-bottom: 0; }
    Section > Contents { padding: 0 0 0 2; }
    Section .rows { height: auto; }
    Section .picker-bar { height: auto; }
    Section .picker { width: 1fr; }
    Section .picker-bar Button { width: auto; min-width: 0; margin-left: 1; }
    """

    def __init__(self, editor: ServiceEditor, name: str) -> None:
        self.editor = editor
        self.section = name
        self._rows_box = Vertical(classes="rows")
        self._picker = Select([], allow_blank=True, compact=True, classes="picker")
        self._info = Button(tr("Info"), classes="pick-info", compact=True)
        self._add = Button(tr("Add"), classes="pick-add", compact=True, variant="primary")
        bar = Horizontal(self._picker, self._info, self._add, classes="picker-bar")
        super().__init__(self._rows_box, bar, title=Content(f"[{name}]"), collapsed=False)

    def on_mount(self) -> None:
        self._refresh_choices()

    def row_list(self) -> list[Row]:
        return [child for child in self._rows_box.children if isinstance(child, Row)]

    def entries(self) -> list[Entry]:
        return [row.to_entry() for row in self.row_list()]

    def _refresh_choices(self) -> None:
        used = {row.directive.key for row in self.row_list()}
        choices = [
            (d.key, d.key)
            for d in directives.CATALOG
            if d.section == self.section and (d.repeatable or d.key not in used)
        ]
        self._picker.set_options(choices)
        self._picker.prompt = tr("Add directive…")
        self._info.disabled = self._add.disabled = not choices

    def _picked(self) -> Directive | None:
        key = self._picker.value
        return directives.lookup(self.section, key) if isinstance(key, str) else None

    async def load(self, entries: list[Entry]) -> None:
        await self._rows_box.remove_children()
        rows = []
        for e in entries:
            known = directives.lookup(self.section, e.key)
            rows.append(Row(self, known or directives.unknown(self.section, e.key), e))
        await self._rows_box.mount_all(rows)
        self._refresh_choices()

    async def add(self, directive: Directive) -> Row:
        row = Row(self, directive, Entry(directive.key, directives.initial_value(directive)))
        await self._rows_box.mount(row)
        self._refresh_choices()
        self.editor.form_changed()
        return row

    async def remove_row(self, row: Row) -> None:
        rows = self.row_list()
        index = rows.index(row)
        await row.remove()
        self._refresh_choices()
        self.editor.form_changed()
        rest = self.row_list()
        if rest:
            rest[min(index, len(rest) - 1)].focus_field()
        else:
            self._picker.focus()

    def move_row(self, row: Row, delta: int) -> None:
        rows = self.row_list()
        index = rows.index(row) + delta
        if not 0 <= index < len(rows):
            return
        if delta < 0:
            self._rows_box.move_child(row, before=rows[index])
        else:
            self._rows_box.move_child(row, after=rows[index])
        row.focus_field()
        self.editor.form_changed()

    @on(Select.Changed, ".picker")
    def _picker_changed(self, event: Select.Changed) -> None:
        event.stop()  # choosing is not adding: Add does that

    @on(Button.Pressed, ".pick-info")
    def _show_info(self, event: Button.Pressed) -> None:
        event.stop()
        picked = self._picked()
        if picked is not None:
            self.app.push_screen(InfoScreen(picked))

    @on(Button.Pressed, ".pick-add")
    async def _add_picked(self, event: Button.Pressed) -> None:
        event.stop()
        picked = self._picked()
        if picked is None:
            self.app.bell()
            return
        row = await self.add(picked)
        row.focus_field()


class ServiceEditor(Vertical):
    """Builder and Text tabs over one unit file text (``text``, what gets saved); extra
    TabPanes given to the constructor are appended after them."""

    DEFAULT_CSS = """
    ServiceEditor { height: 1fr; }
    ServiceEditor TabbedContent { height: 1fr; }
    ServiceEditor TabPane { padding: 0; }
    ServiceEditor #builder-box { height: 1fr; }
    ServiceEditor #form { width: 1fr; }
    ServiceEditor #preview-box { width: 1fr; }
    ServiceEditor #preview-box > TextArea { height: 1fr; }
    ServiceEditor Section { margin-bottom: 1; }
    ServiceEditor #hint { height: auto; max-height: 2; padding: 0 1; color: $text-muted; }
    ServiceEditor #hint.warning { color: $warning; }
    """
    BINDINGS = [
        Binding("f2", "tab('builder')", "Builder"),
        Binding("f3", "tab('text')", "Text"),
    ]

    def __init__(self, *extra: TabPane, id: str | None = None) -> None:
        super().__init__(id=id)
        self._extra = extra
        self._doc = unitparse.UnitText()
        self._synced = ""  # text the form was last loaded from or rendered to

    def compose(self) -> ComposeResult:
        with TabbedContent(id="editor-tabs"):
            with TabPane(tr("Builder"), id="builder"):
                with Horizontal(id="builder-box"):
                    with VerticalScroll(id="form"):
                        for name in SECTIONS:
                            yield Section(self, name)
                    with Vertical(id="preview-box"):
                        yield Label(tr("Preview of the unit file:"))
                        yield TextArea(id="preview", read_only=True, show_line_numbers=True)
            with TabPane(tr("Text"), id="text"):
                yield TextArea(id="editor", show_line_numbers=True)
            yield from self._extra
        yield Static(id="hint")

    # ---- text ---------------------------------------------------------------------------------

    @property
    def text(self) -> str:
        return self.query_one("#editor", TextArea).text

    async def set_text(self, text: str) -> None:
        self.query_one("#editor", TextArea).load_text(text)
        await self._load_form()

    async def _load_form(self) -> None:
        """Text -> form."""
        text = self.text
        self._doc = unitparse.parse(text)
        first = unitparse.first_entries(self._doc, SECTIONS)
        for section in self.query(Section):
            await section.load(first[section.section])
        self._synced = text
        self._show_preview(text)

    def form_changed(self) -> None:
        """Form -> text."""
        entries = {s.section: s.entries() for s in self.query(Section)}
        text = unitparse.serialize(unitparse.merge(self._doc, entries, SECTIONS))
        if text != self.text:
            self.query_one("#editor", TextArea).load_text(text)
        self._synced = text
        self._show_preview(text)

    def _show_preview(self, text: str) -> None:
        preview = self.query_one("#preview", TextArea)
        if preview.text != text:
            scroll = preview.scroll_offset
            preview.load_text(text)
            preview.scroll_to(scroll.x, scroll.y, animate=False)

    def focus_first(self) -> None:
        """Focus the first field of the form, or the first directive picker."""
        for section in self.query(Section):
            rows = section.row_list()
            if rows:
                rows[0].focus_field()
                return
        self.query_one(Section).query_one(".picker").focus()

    # ---- tabs, layout, hints ------------------------------------------------------------------

    def action_tab(self, pane: str) -> None:
        """Switch tab and move the focus into it: TabbedContent goes back to the tab that
        holds the focused widget."""
        tabs = self.query_one("#editor-tabs", TabbedContent)
        tabs.active = pane
        if pane == "builder":
            self.focus_first()
            return
        focusable = [w for w in tabs.get_pane(pane).query("*") if w.focusable]
        if focusable:
            focusable[0].focus()

    @on(TabbedContent.TabActivated)
    async def _tab_activated(self, event: TabbedContent.TabActivated) -> None:
        event.stop()
        if event.pane.id == "builder" and self.text != self._synced:
            await self._load_form()
            self.focus_first()  # the focused row may have been replaced

    def on_resize(self) -> None:
        self.query_one("#preview-box").display = self.size.width >= WIDE

    def on_descendant_blur(self) -> None:
        self.show_hint(None)

    def on_descendant_focus(self, event) -> None:
        widgets = event.widget.ancestors_with_self
        self.show_hint(next((w for w in widgets if isinstance(w, Row)), None))

    def show_hint(self, row: Row | None) -> None:
        """Under the tabs: the problem of the focused row, else what its directive does."""
        hint = self.query_one("#hint", Static)
        text = ""
        if row is not None:
            text = row.problem or (tr(row.directive.info) if row.directive.info else "")
        hint.update(Content(text))
        hint.set_class(row is not None and bool(row.problem), "warning")
