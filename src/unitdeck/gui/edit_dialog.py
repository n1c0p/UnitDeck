# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Nicola Palmieri (n1c0p)
"""Modal editor for one unit: drop-in (default for package units) or the unit file itself."""

from __future__ import annotations

import os

from PyQt6.QtCore import QProcess, Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from unitdeck.backend import unitfiles
from unitdeck.backend.base import SystemdBackend, Unit
from unitdeck.gui.code_editor import CodeEditor
from unitdeck.gui.service_form import ServiceEditor
from unitdeck.i18n import tr
from unitdeck.messages import dropin_template


class EditDialog(QDialog):
    """Returns Accepted after a successful save; ``saved_content`` holds what was written."""

    def __init__(self, backend: SystemdBackend, unit: Unit, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._backend = backend
        self._unit = unit
        self._own = backend.own_dir
        self._package = not unit.own  # shipped by a package (or generated): edit through a drop-in
        self._mode = "dropin" if self._package else "unit"
        self._staged = ""
        self.saved_content = ""
        self.setWindowTitle(tr("Edit – {unit}").format(unit=unit.name))
        self.resize(1150, 720)

        self._info = QLabel()
        self._info.setWordWrap(True)
        self._info.setTextFormat(Qt.TextFormat.RichText)
        self._copy = QCheckBox(
            tr("Edit a full copy of the unit instead of a drop-in (not recommended)")
        )
        self._copy.setVisible(self._package)
        self._copy.toggled.connect(self._switch_mode)

        self._editor = ServiceEditor()
        self._effective = CodeEditor()
        self._effective.setReadOnly(True)
        effective_label = QLabel(tr("Effective configuration (unit file and drop-ins):"))
        effective = QWidget()
        effective_layout = QVBoxLayout(effective)
        effective_layout.addWidget(effective_label)
        effective_layout.addWidget(self._effective)
        self._editor.tabs.addTab(effective, tr("Effective configuration"))

        self._output = QPlainTextEdit()
        self._output.setReadOnly(True)
        self._output.setMaximumHeight(110)
        self._output.hide()

        self._verify_btn = QPushButton(tr("Verify"))
        self._save_btn = QPushButton(tr("Save"))
        self._save_btn.setDefault(True)
        cancel = QPushButton(tr("Cancel"))
        buttons = QHBoxLayout()
        buttons.addWidget(self._verify_btn)
        buttons.addStretch(1)
        buttons.addWidget(cancel)
        buttons.addWidget(self._save_btn)

        layout = QVBoxLayout(self)
        layout.addWidget(self._info)
        layout.addWidget(self._copy)
        layout.addWidget(self._editor, 1)
        layout.addWidget(self._output)
        layout.addLayout(buttons)

        self._verify_btn.clicked.connect(lambda: self._verify(then=None))
        self._save_btn.clicked.connect(self._save)
        cancel.clicked.connect(self.reject)
        backend.unit_updated.connect(self._on_unit_updated)
        backend.writer.finished.connect(self._on_written)

        self._load()
        self._show_effective()
        backend.fetch_details(unit.name)  # fills the drop-in list for the effective view

    # ---- content ----------------------------------------------------------------------------

    def target_path(self) -> str:
        if self._mode == "dropin":
            return unitfiles.dropin_path(self._unit.name, self._own)
        return unitfiles.unit_path(self._unit.name, self._own)

    def _load(self) -> None:
        target = self.target_path()
        if self._mode == "dropin":
            text = (
                unitfiles.read_text(target)
                if os.path.exists(target)
                else dropin_template(self._unit.name)
            )
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
        self._info.setText(
            info.format(
                path=f"<code>{self._unit.fragment_path}</code>", dropin=f"<code>{target}</code>"
            )
        )
        self._editor.setPlainText(text)
        self._editor.document().setModified(False)

    def _switch_mode(self, copy: bool) -> None:
        if self._editor.document().isModified():
            answer = QMessageBox.question(
                self, "UnitDeck", tr("Discard the changes in the editor?")
            )
            if answer != QMessageBox.StandardButton.Yes:
                self._copy.blockSignals(True)
                self._copy.setChecked(not copy)
                self._copy.blockSignals(False)
                return
        self._mode = "copy" if copy else "dropin"
        self._load()

    def _show_effective(self) -> None:
        unit = self._backend.units.get(self._unit.name, self._unit)
        parts = [
            f"# {path}\n{text}"
            for path, text in unitfiles.effective_config(unit.fragment_path, unit.drop_in_paths)
        ]
        self._effective.setPlainText("\n".join(parts))

    def _on_unit_updated(self, name: str) -> None:
        if name == self._unit.name:
            self._show_effective()

    # ---- verify and save --------------------------------------------------------------------

    def _verify(self, then) -> None:
        """Run systemd-analyze verify on a staged copy; ``then(ok)`` continues after the result."""
        content = self._editor.toPlainText()
        if self._mode == "dropin":
            self._staged = unitfiles.stage_for_verify(
                self._unit.name, unitfiles.read_text(self._unit.fragment_path), content
            )
        else:
            self._staged = unitfiles.stage_for_verify(self._unit.name, content)
        self._set_busy(True, tr("Verifying…"))
        proc = QProcess(self)
        proc.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        proc.finished.connect(lambda code, _status: self._verified(proc, code, then))
        proc.start("systemd-analyze", unitfiles.verify_args(self._backend.scope, self._staged))

    def _verified(self, proc: QProcess, code: int, then) -> None:
        output = bytes(proc.readAllStandardOutput()).decode("utf-8", "replace")
        proc.deleteLater()
        lines = unitfiles.relevant_lines(output, self._staged)
        unitfiles.cleanup_staging(self._staged)
        ok = code == 0
        if ok and not lines:
            self._set_busy(False, tr("systemd-analyze verify: no problems found."))
        else:
            self._set_busy(
                False,
                (
                    tr("systemd-analyze verify found errors:")
                    if not ok
                    else tr("systemd-analyze verify warnings:")
                )
                + "\n"
                + lines,
            )
        if then is not None:
            then(ok)

    def _save(self) -> None:
        self._verify(then=self._write)

    def _write(self, verified: bool) -> None:
        if not verified:
            answer = QMessageBox.warning(
                self,
                "UnitDeck",
                tr("systemd-analyze verify reported errors. Save anyway?"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
        self.saved_content = self._editor.toPlainText()
        if self.saved_content and not self.saved_content.endswith("\n"):
            self.saved_content += "\n"
        self._set_busy(True, tr("Saving…"))
        if self._mode == "dropin":
            self._backend.writer.write_dropin(self._unit.name, self.saved_content)
        else:
            self._backend.writer.write_unit(self._unit.name, self.saved_content)

    def _on_written(self, operation: str, ok: bool, detail: str) -> None:
        if operation != "save":
            return
        if ok:
            self.accept()
        else:
            self._set_busy(False, "")  # the tab shows the error

    def _set_busy(self, busy: bool, message: str) -> None:
        self._save_btn.setEnabled(not busy)
        self._verify_btn.setEnabled(not busy)
        self._output.setVisible(bool(message))
        self._output.setPlainText(message)
