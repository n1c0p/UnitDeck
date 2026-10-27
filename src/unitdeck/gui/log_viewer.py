# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Nicola Palmieri (n1c0p)
"""Journal window for one unit: last N lines, live follow, priority filter."""

from __future__ import annotations

import html

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFontDatabase
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from unitdeck.backend.base import Runtime, Scope
from unitdeck.backend.journal import PRIORITIES, JournalReader
from unitdeck.i18n import tr

PRIORITY_COLORS = {0: "#d1242f", 1: "#d1242f", 2: "#d1242f", 3: "#d1242f", 4: "#bf8700"}


class LogViewer(QDialog):
    def __init__(
        self, unit: str, scope: Scope, runtime: Runtime, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self._unit = unit
        self._scope = scope
        self.setWindowTitle(tr("Logs – {unit}").format(unit=unit))
        self.setWindowFlag(Qt.WindowType.Window)  # independent window, not a modal child
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.resize(900, 500)

        self._priority = QComboBox()
        for i, name in enumerate(PRIORITIES):
            self._priority.addItem(f"{i} {name}", i)
        self._priority.setCurrentIndex(len(PRIORITIES) - 1)
        self._priority.setToolTip(tr("Show messages with this priority or more severe"))
        self._lines = QSpinBox()
        self._lines.setRange(50, 20000)
        self._lines.setSingleStep(100)
        self._lines.setValue(500)
        self._follow = QCheckBox(tr("Follow (live)"))
        reload = QPushButton(tr("Reload"))

        bar = QHBoxLayout()
        bar.addWidget(QLabel(tr("Priority:")))
        bar.addWidget(self._priority)
        bar.addWidget(QLabel(tr("Lines:")))
        bar.addWidget(self._lines)
        bar.addWidget(self._follow)
        bar.addStretch(1)
        bar.addWidget(reload)

        self._text = QPlainTextEdit()
        self._text.setReadOnly(True)
        self._text.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont))
        self._text.setMaximumBlockCount(50000)

        layout = QVBoxLayout(self)
        layout.addLayout(bar)
        layout.addWidget(self._text)

        self._reader = JournalReader(runtime)
        self._reader.entry.connect(self._append)
        self._reader.finished.connect(self._on_finished)
        self._priority.currentIndexChanged.connect(self.restart)
        self._lines.editingFinished.connect(self.restart)
        self._follow.toggled.connect(self.restart)
        reload.clicked.connect(self.restart)
        self.restart()

    def restart(self) -> None:
        self._text.clear()
        self._reader.start(
            self._unit,
            self._scope,
            self._lines.value(),
            self._priority.currentData(),
            self._follow.isChecked(),
        )

    def _append(self, line: str, priority: int) -> None:
        text = html.escape(line)
        color = PRIORITY_COLORS.get(priority)
        self._text.appendHtml(f'<span style="color:{color}">{text}</span>' if color else text)
        self._text.verticalScrollBar().setValue(self._text.verticalScrollBar().maximum())

    def _on_finished(self, code: int, stderr: str) -> None:
        if self._text.blockCount() <= 1 and not self._text.toPlainText():
            self._text.appendHtml(f"<i>{tr('No journal entries for this unit.')}</i>")
        if stderr:  # e.g. the hint that only members of adm/systemd-journal see the system journal
            self._text.appendHtml(f"<i>journalctl: {html.escape(stderr)}</i>")

    def closeEvent(self, event) -> None:
        self._reader.stop()
        super().closeEvent(event)
