# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Nicola Palmieri (n1c0p)
"""Four-step wizard that creates a new .service unit from a template."""

from __future__ import annotations

import os
import re

from PyQt6.QtCore import QProcess
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QWizard,
    QWizardPage,
)

from unitdeck.backend import unitfiles
from unitdeck.backend.base import Scope, SystemdBackend
from unitdeck.gui.code_editor import CodeEditor
from unitdeck.i18n import tr
from unitdeck.templates import Template, load_templates, render

NAME_RE = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_.:-]{0,245}$")
TYPES = ("simple", "exec", "forking", "oneshot", "dbus", "notify", "idle")
RESTARTS = ("no", "on-success", "on-failure", "on-abnormal", "on-abort", "always")
LABELS = {  # placeholder -> field label (source strings, translated with tr())
    "DESCRIPTION": "Description",
    "TYPE": "Type",
    "EXEC_START": "Command (ExecStart)",
    "EXEC_STOP": "Stop command (ExecStop)",
    "RESTART": "Restart policy (Restart)",
    "AFTER": "Start after (After)",
    "WANTS": "Wants",
    "USER": "User",
    "GROUP": "Group",
    "WANTED_BY": "Wanted by (WantedBy)",
    "SERVER": "Server",
    "SHARE": "Share",
    "CREDENTIALS_FILE": "Credentials file (relative to home)",
}
REQUIRED = ("EXEC_START", "SERVER", "SHARE", "CREDENTIALS_FILE")


def placeholder_label(name: str) -> str:
    return tr(LABELS[name]) if name in LABELS else name.replace("_", " ").capitalize()


def normalize_name(text: str) -> str:
    text = text.strip()
    return text if text.endswith(".service") or not text else text + ".service"


def name_problem(name: str, backend: SystemdBackend) -> str:
    """'' when the name is valid and free in every systemd search path, else the reason."""
    stem = name[: -len(".service")] if name.endswith(".service") else name
    if not NAME_RE.match(stem):
        return tr("Use letters, digits, '-', '_', '.' and ':' only.")
    if name in backend.units or os.path.lexists(unitfiles.unit_path(name, backend.own_dir)):
        return tr("A unit with this name already exists.")
    for directory in unitfiles.OTHER_UNIT_DIRS[backend.scope]:
        if os.path.lexists(os.path.join(directory, name)):
            return tr("A unit with this name already exists.")
    return ""


class NewServiceWizard(QWizard):
    """After ``exec()`` returns Accepted: ``unit_name``, ``content``, ``enable`` and ``start``."""

    def __init__(self, backend: SystemdBackend, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._backend = backend
        self.unit_name = ""
        self.content = ""
        self.enable = False
        self.start = False
        self._saving = False
        self.setWindowTitle(tr("New service"))
        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)
        self.resize(900, 650)
        self.addPage(_NamePage(backend))
        self.addPage(_FieldsPage(backend))
        self.addPage(_PreviewPage(backend))
        self.addPage(_OptionsPage(backend))
        backend.writer.finished.connect(self._on_written)

    def accept(self) -> None:
        """Finish: write the unit; the dialog closes only when the writer succeeded."""
        if self._saving:
            return
        self.unit_name = self.field("name")
        self.content = self.page(2).content()
        self.enable = self.field("enable")
        self.start = self.field("start")
        self._saving = True
        self.button(QWizard.WizardButton.FinishButton).setEnabled(False)
        self._backend.writer.write_unit(self.unit_name, self.content)

    def _on_written(self, operation: str, ok: bool, _detail: str) -> None:
        if operation != "save" or not self._saving:
            return
        self._saving = False
        if ok:
            super().accept()
        else:
            self.button(QWizard.WizardButton.FinishButton).setEnabled(True)


class _NamePage(QWizardPage):
    def __init__(self, backend: SystemdBackend) -> None:
        super().__init__()
        self._backend = backend
        self.setTitle(tr("Name and template"))
        self._name = QLineEdit()
        self._name.setPlaceholderText(tr("my-service"))
        self._error = QLabel()
        self._error.setStyleSheet("color: #d1242f")
        self._templates = QListWidget()
        for template in load_templates():
            if template.fits(backend.scope.value):
                item = QListWidgetItem(tr(template.name))
                item.setData(0x0100, template)
                self._templates.addItem(item)
        self._templates.setCurrentRow(0)
        layout = QFormLayout(self)
        layout.addRow(tr("Service name:"), self._name)
        layout.addRow("", self._error)
        layout.addRow(tr("Template:"), self._templates)
        self.registerField("name*", self._name)
        self._name.textChanged.connect(self._check)
        self._templates.currentRowChanged.connect(lambda _row: self.completeChanged.emit())

    def template(self) -> Template | None:
        item = self._templates.currentItem()
        return item.data(0x0100) if item is not None else None

    def unit_name(self) -> str:
        return normalize_name(self._name.text())

    def _check(self) -> None:
        self._error.setText(
            name_problem(self.unit_name(), self._backend) if self._name.text() else ""
        )
        self.completeChanged.emit()

    def isComplete(self) -> bool:
        return bool(self._name.text()) and not self._error.text() and self.template() is not None

    def validatePage(self) -> bool:
        self.setField("name", self.unit_name())
        return True


class _FieldsPage(QWizardPage):
    def __init__(self, backend: SystemdBackend) -> None:
        super().__init__()
        self._backend = backend
        self.setTitle(tr("Guided fields"))
        self._form = QFormLayout(self)
        self._widgets: dict[str, QWidget] = {}
        self._template: Template | None = None

    def initializePage(self) -> None:
        template = self.wizard().page(0).template()
        if template is self._template:
            return
        self._template = template
        while self._form.rowCount():
            self._form.removeRow(0)
        self._widgets = {}
        system = self._backend.scope is Scope.SYSTEM
        for name in template.placeholders:
            if name in ("USER", "GROUP") and not system:
                continue  # user services already run as the user
            widget: QWidget
            if name == "TYPE":
                widget = QComboBox()
                widget.addItems(TYPES)
            elif name == "RESTART":
                widget = QComboBox()
                widget.addItems(RESTARTS)
            else:
                widget = QLineEdit()
                if name == "WANTED_BY":
                    widget.setText("multi-user.target" if system else "default.target")
                elif name == "EXEC_START":
                    widget.setPlaceholderText("/usr/bin/program --option")
                elif name == "AFTER":
                    widget.setPlaceholderText("network-online.target")
                if name in REQUIRED:
                    widget.textChanged.connect(lambda _t: self.completeChanged.emit())
            self._widgets[name] = widget
            self._form.addRow(placeholder_label(name) + ":", widget)
        if system and "USER" in self._widgets:
            note = QLabel(tr("Without User= and Group= the service runs as root."))
            note.setWordWrap(True)
            self._form.addRow("", note)
        self.completeChanged.emit()

    def values(self) -> dict[str, str]:
        values = {}
        for name, widget in self._widgets.items():
            values[name] = widget.currentText() if isinstance(widget, QComboBox) else widget.text()
        return values

    def isComplete(self) -> bool:
        return all(
            self.values().get(name, "x").strip() for name in REQUIRED if name in self._widgets
        )


class _PreviewPage(QWizardPage):
    def __init__(self, backend: SystemdBackend) -> None:
        super().__init__()
        self._backend = backend
        self._rendered = ""
        self._staged = ""
        self.setTitle(tr("Preview"))
        self._editor = CodeEditor()
        self._output = QPlainTextEdit()
        self._output.setReadOnly(True)
        self._output.setMaximumHeight(90)
        verify = QPushButton(tr("Verify"))
        verify.clicked.connect(self.verify)
        row = QHBoxLayout()
        row.addWidget(QLabel(tr("Generated unit file, editable by hand:")))
        row.addStretch(1)
        row.addWidget(verify)
        layout = QVBoxLayout(self)
        layout.addLayout(row)
        layout.addWidget(self._editor, 1)
        layout.addWidget(self._output)

    def initializePage(self) -> None:
        wizard = self.wizard()
        rendered = render(wizard.page(0).template(), wizard.page(1).values())
        if rendered != self._rendered or not self._editor.document().isModified():
            self._rendered = rendered
            self._editor.setPlainText(rendered)
            self._editor.document().setModified(False)
        self.verify()

    def content(self) -> str:
        text = self._editor.toPlainText()
        return text if text.endswith("\n") else text + "\n"

    def verify(self) -> None:
        self._staged = unitfiles.stage_for_verify(self.field("name"), self.content())
        self._output.setPlainText(tr("Verifying…"))
        proc = QProcess(self)
        proc.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        proc.finished.connect(lambda code, _status: self._verified(proc, code))
        proc.start("systemd-analyze", unitfiles.verify_args(self._backend.scope, self._staged))

    def _verified(self, proc: QProcess, code: int) -> None:
        output = bytes(proc.readAllStandardOutput()).decode("utf-8", "replace")
        proc.deleteLater()
        lines = unitfiles.relevant_lines(output, self._staged)
        unitfiles.cleanup_staging(self._staged)
        if code == 0 and not lines:
            self._output.setPlainText(tr("systemd-analyze verify: no problems found."))
        elif code == 0:
            self._output.setPlainText(tr("systemd-analyze verify warnings:") + "\n" + lines)
        else:
            self._output.setPlainText(tr("systemd-analyze verify found errors:") + "\n" + lines)


class _OptionsPage(QWizardPage):
    def __init__(self, backend: SystemdBackend) -> None:
        super().__init__()
        self._backend = backend
        self.setTitle(tr("Final options"))
        self._where = QLabel()
        self._where.setWordWrap(True)
        enable = QCheckBox(tr("Enable at boot"))
        start = QCheckBox(tr("Start now"))
        enable.setChecked(True)
        start.setChecked(True)
        layout = QVBoxLayout(self)
        layout.addWidget(self._where)
        layout.addWidget(enable)
        layout.addWidget(start)
        layout.addStretch(1)
        self.registerField("enable", enable)
        self.registerField("start", start)

    def initializePage(self) -> None:
        path = unitfiles.unit_path(self.field("name"), self._backend.own_dir)
        text = tr("The unit will be written to {path}.")
        if self._backend.scope is Scope.SYSTEM:
            text += " " + tr("The system will ask for your password.")
        self._where.setText(text.format(path=f"<code>{path}</code>"))
