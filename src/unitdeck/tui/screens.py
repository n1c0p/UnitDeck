# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Nicola Palmieri (n1c0p)
"""Modal screens of the terminal interface: confirmation, unit editor, new service."""

from __future__ import annotations

import os
from collections.abc import Callable

from rich.markup import escape
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Checkbox, Footer, Input, Label, Select, Static, TextArea

from unitdeck.backend import unitfiles
from unitdeck.backend.base import Scope, SystemdBackend, Unit
from unitdeck.i18n import tr
from unitdeck.messages import dropin_template
from unitdeck.newservice import (
    REQUIRED,
    RESTARTS,
    TYPES,
    name_problem,
    normalize_name,
    placeholder_label,
)
from unitdeck.templates import Template, load_templates, render


class ConfirmScreen(ModalScreen[bool]):
    """Yes / No question; dismissed with the answer."""

    DEFAULT_CSS = """
    ConfirmScreen { align: center middle; }
    ConfirmScreen > Vertical { width: 70; height: auto; border: thick $primary; padding: 1 2; }
    ConfirmScreen Horizontal { height: auto; align: right middle; }
    ConfirmScreen Button { margin-left: 2; }
    """
    BINDINGS = [Binding("escape", "answer(False)", "No"), Binding("y", "answer(True)", "Yes")]

    def __init__(self, question: str) -> None:
        super().__init__()
        self._question = question

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label(self._question)
            with Horizontal():
                yield Button(tr("No"), id="no")
                yield Button(tr("Yes"), id="yes", variant="primary")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "yes")

    def action_answer(self, answer: bool) -> None:
        self.dismiss(answer)


class _Verifier:
    """Stage a unit (and drop-in) and run systemd-analyze verify through the runtime."""

    def __init__(self, backend: SystemdBackend) -> None:
        self._backend = backend

    def verify(
        self,
        unit_name: str,
        unit_text: str,
        dropin_text: str | None,
        then: Callable[[bool, str], None],
    ) -> None:
        staged = unitfiles.stage_for_verify(unit_name, unit_text, dropin_text)
        args = ["systemd-analyze", *unitfiles.verify_args(self._backend.scope, staged)]

        def done(code: int, out: str, err: str) -> None:
            lines = unitfiles.relevant_lines(out + err, staged)
            unitfiles.cleanup_staging(staged)
            then(code == 0, lines)

        self._backend.runtime.run(args, None, done)


class EditScreen(ModalScreen[bool]):
    """Drop-in editor for package units, direct editor for user-created ones; True when saved."""

    DEFAULT_CSS = """
    EditScreen > #info {
        dock: top; height: auto; padding: 0 1; background: $primary; color: $text;
    }
    EditScreen > Horizontal { height: 1fr; }
    EditScreen > Horizontal > TextArea { width: 1fr; }
    EditScreen > #output {
        dock: bottom; height: auto; max-height: 6; padding: 0 1; color: $warning;
    }
    """
    BINDINGS = [
        Binding("ctrl+s", "save", "Save"),
        Binding("ctrl+v", "verify", "Verify"),
        Binding("ctrl+t", "toggle_copy", "Drop-in/Copy"),
        Binding("escape", "cancel", "Cancel"),
    ]

    def __init__(self, backend: SystemdBackend, unit: Unit) -> None:
        super().__init__()
        self._backend = backend
        self._unit = unit
        self._mode = "dropin" if not unit.own else "unit"
        self._verifier = _Verifier(backend)

    def compose(self) -> ComposeResult:
        yield Static(id="info")
        with Horizontal():
            yield TextArea(id="editor", show_line_numbers=True)
            yield TextArea(id="effective", read_only=True, show_line_numbers=True)
        yield Static(id="output")
        yield Footer()

    def on_mount(self) -> None:
        self._load()
        self._show_effective()
        self._backend.unit_updated.connect(self._on_updated)
        self._backend.writer.finished.connect(self._on_written)
        self._backend.fetch_details(self._unit.name)
        self.query_one("#editor", TextArea).focus()

    def on_unmount(self) -> None:
        self._backend.unit_updated.disconnect(self._on_updated)
        self._backend.writer.finished.disconnect(self._on_written)

    def target_path(self) -> str:
        if self._mode == "dropin":
            return unitfiles.dropin_path(self._unit.name, self._backend.own_dir)
        return unitfiles.unit_path(self._unit.name, self._backend.own_dir)

    def _load(self) -> None:
        target = self.target_path()
        if self._mode == "dropin":
            exists = os.path.exists(target)
            text = unitfiles.read_text(target) if exists else dropin_template(self._unit.name)
            info = tr(
                "Package unit {path}: saved as the drop-in {dropin}, kept across package upgrades."
            )
        elif self._mode == "copy":
            source = target if os.path.exists(target) else self._unit.fragment_path
            text = unitfiles.read_text(source)
            info = tr(
                "A full copy in {dropin} shadows {path}: package upgrades no longer reach it."
            )
        else:
            text = unitfiles.read_text(target)
            info = tr("Editing {dropin} directly.")
        self.query_one("#info", Static).update(
            escape(info.format(path=self._unit.fragment_path, dropin=target))
        )
        self.query_one("#editor", TextArea).load_text(text)

    def _show_effective(self) -> None:
        unit = self._backend.units.get(self._unit.name, self._unit)
        parts = [
            f"# {path}\n{text}"
            for path, text in unitfiles.effective_config(unit.fragment_path, unit.drop_in_paths)
        ]
        self.query_one("#effective", TextArea).load_text("\n".join(parts))

    def _on_updated(self, name: str) -> None:
        if name == self._unit.name:
            self._show_effective()

    def _content(self) -> str:
        text = self.query_one("#editor", TextArea).text
        return text if text.endswith("\n") else text + "\n"

    def _message(self, text: str) -> None:
        self.query_one("#output", Static).update(escape(text))

    def action_toggle_copy(self) -> None:
        if self._unit.own:
            return
        self._mode = "copy" if self._mode == "dropin" else "dropin"
        self._load()

    def action_verify(self) -> None:
        self._run_verify(lambda ok, lines: None)

    def _run_verify(self, then: Callable[[bool, str], None]) -> None:
        self._message(tr("Verifying…"))
        content = self._content()
        if self._mode == "dropin":
            unit_text, dropin = unitfiles.read_text(self._unit.fragment_path), content
        else:
            unit_text, dropin = content, None

        def done(ok: bool, lines: str) -> None:
            if ok and not lines:
                self._message(tr("systemd-analyze verify: no problems found."))
            else:
                head = (
                    tr("systemd-analyze verify warnings:")
                    if ok
                    else tr("systemd-analyze verify found errors:")
                )
                self._message(head + "\n" + lines)
            then(ok, lines)

        self._verifier.verify(self._unit.name, unit_text, dropin, done)

    def action_save(self) -> None:
        def after_verify(ok: bool, _lines: str) -> None:
            if ok:
                self._write()
            else:
                self.app.push_screen(
                    ConfirmScreen(tr("systemd-analyze verify reported errors. Save anyway?")),
                    lambda answer: self._write() if answer else None,
                )

        self._run_verify(after_verify)

    def _write(self) -> None:
        self._message(tr("Saving…"))
        content = self._content()
        if self._mode == "dropin":
            self._backend.writer.write_dropin(self._unit.name, content)
        else:
            self._backend.writer.write_unit(self._unit.name, content)

    def _on_written(self, operation: str, ok: bool, _detail: str) -> None:
        if operation == "save" and ok:
            self.dismiss(True)

    def action_cancel(self) -> None:
        self.dismiss(False)


class NewServiceScreen(ModalScreen[dict | None]):
    """One form: name, template, its fields, preview with verify, enable/start options."""

    DEFAULT_CSS = """
    NewServiceScreen > VerticalScroll { padding: 0 1; }
    NewServiceScreen Label { margin-top: 1; }
    NewServiceScreen #error { color: $error; }
    NewServiceScreen #preview { height: 14; }
    NewServiceScreen #output { color: $warning; height: auto; max-height: 5; }
    NewServiceScreen Horizontal { height: auto; }
    NewServiceScreen Button { margin: 1 2 0 0; }
    """
    BINDINGS = [Binding("escape", "cancel", "Cancel"), Binding("ctrl+v", "verify", "Verify")]

    def __init__(self, backend: SystemdBackend) -> None:
        super().__init__()
        self._backend = backend
        self._templates = [t for t in load_templates() if t.fits(backend.scope.value)]
        self._template: Template = self._templates[0]
        self._verifier = _Verifier(backend)
        self._saving = False

    def compose(self) -> ComposeResult:
        with VerticalScroll():
            yield Label(tr("Service name:"))
            yield Input(placeholder=tr("my-service"), id="name")
            yield Static(id="error")
            yield Label(tr("Template:"))
            yield Select(
                [(tr(t.name), i) for i, t in enumerate(self._templates)],
                value=0,
                allow_blank=False,
                id="template",
            )
            yield Vertical(id="fields")
            yield Label(tr("Generated unit file, editable by hand:"))
            yield TextArea(id="preview", show_line_numbers=True)
            yield Static(id="output")
            yield Checkbox(tr("Enable at boot"), value=True, id="enable")
            yield Checkbox(tr("Start now"), value=True, id="start")
            with Horizontal():
                yield Button(tr("Verify"), id="verify")
                yield Button(tr("Create"), id="create", variant="primary")
                yield Button(tr("Cancel"), id="cancel")
        yield Footer()

    async def on_mount(self) -> None:
        self._backend.writer.finished.connect(self._on_written)
        await self._build_fields()
        self.query_one("#name", Input).focus()

    def on_unmount(self) -> None:
        self._backend.writer.finished.disconnect(self._on_written)

    # ---- form -------------------------------------------------------------------------------

    async def _build_fields(self) -> None:
        box = self.query_one("#fields", Vertical)
        await box.remove_children()  # removal is asynchronous: wait, or the ids would collide
        system = self._backend.scope is Scope.SYSTEM
        children: list = []
        for name in self._template.placeholders:
            if name in ("USER", "GROUP") and not system:
                continue
            children.append(Label(placeholder_label(name) + ":"))
            if name == "TYPE":
                options = [(t, t) for t in TYPES]
                children.append(Select(options, value="simple", allow_blank=False, id=f"f-{name}"))
            elif name == "RESTART":
                options = [(r, r) for r in RESTARTS]
                children.append(Select(options, value="no", allow_blank=False, id=f"f-{name}"))
            else:
                default = ""
                if name == "WANTED_BY":
                    default = "multi-user.target" if system else "default.target"
                children.append(Input(value=default, id=f"f-{name}"))
        if system and "USER" in self._template.placeholders:
            children.append(Static(tr("Without User= and Group= the service runs as root.")))
        await box.mount_all(children)  # wait: a Select reads its own children right after mounting
        self._render_preview()

    def _values(self) -> dict[str, str]:
        values = {}
        for name in self._template.placeholders:
            widgets = self.query(f"#f-{name}")
            if not widgets:
                continue
            widget = widgets.first()
            values[name] = str(widget.value) if widget.value is not None else ""
        return values

    def unit_name(self) -> str:
        return normalize_name(self.query_one("#name", Input).value)

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "name":
            problem = name_problem(self.unit_name(), self._backend) if event.value else ""
            self.query_one("#error", Static).update(escape(problem))
        self._render_preview()

    async def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "template":
            self._template = self._templates[int(event.value)]
            await self._build_fields()
        self._render_preview()

    def _render_preview(self) -> None:
        self.query_one("#preview", TextArea).load_text(render(self._template, self._values()))

    def _content(self) -> str:
        text = self.query_one("#preview", TextArea).text
        return text if text.endswith("\n") else text + "\n"

    def _message(self, text: str) -> None:
        self.query_one("#output", Static).update(escape(text))

    def _problem(self) -> str:
        name = self.unit_name()
        if not name:
            return tr("Service name:")
        problem = name_problem(name, self._backend)
        if problem:
            return problem
        values = self._values()
        missing = [
            n
            for n in REQUIRED
            if n in self._template.placeholders and not values.get(n, "").strip()
        ]
        if missing:
            return tr("{field} is required.").format(field=placeholder_label(missing[0]))
        return ""

    # ---- actions ----------------------------------------------------------------------------

    def action_verify(self) -> None:
        self._verify(lambda ok, lines: None)

    def _verify(self, then: Callable[[bool, str], None]) -> None:
        name = self.unit_name()
        if not name:
            return
        self._message(tr("Verifying…"))

        def done(ok: bool, lines: str) -> None:
            if ok and not lines:
                self._message(tr("systemd-analyze verify: no problems found."))
            else:
                head = (
                    tr("systemd-analyze verify warnings:")
                    if ok
                    else tr("systemd-analyze verify found errors:")
                )
                self._message(head + "\n" + lines)
            then(ok, lines)

        self._verifier.verify(name, self._content(), None, done)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.dismiss(None)
        elif event.button.id == "verify":
            self.action_verify()
        elif event.button.id == "create":
            self._create()

    def _create(self) -> None:
        problem = self._problem()
        if problem:
            self._message(problem)
            return

        def after_verify(ok: bool, _lines: str) -> None:
            if ok:
                self._write()
            else:
                self.app.push_screen(
                    ConfirmScreen(tr("systemd-analyze verify reported errors. Save anyway?")),
                    lambda answer: self._write() if answer else None,
                )

        self._verify(after_verify)

    def _write(self) -> None:
        self._saving = True
        self._message(tr("Saving…"))
        self._backend.writer.write_unit(self.unit_name(), self._content())

    def _on_written(self, operation: str, ok: bool, _detail: str) -> None:
        if operation == "save" and self._saving:
            self._saving = False
            if ok:
                self.dismiss(
                    {
                        "name": self.unit_name(),
                        "enable": self.query_one("#enable", Checkbox).value,
                        "start": self.query_one("#start", Checkbox).value,
                    }
                )

    def action_cancel(self) -> None:
        self.dismiss(None)
