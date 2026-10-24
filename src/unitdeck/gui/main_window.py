# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Nicola (n1c0p)

from __future__ import annotations

from PyQt6.QtCore import QSettings, Qt, QTimer
from PyQt6.QtWidgets import QComboBox, QMainWindow, QTabWidget

from unitdeck.backend.systemd import UserBackend
from unitdeck.gui.unit_tab import UnitTab
from unitdeck.i18n import set_language, tr


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("UnitDeck")
        self.resize(1150, 650)
        self._settings = QSettings()
        set_language(self._settings.value("language", "system"))
        self._build()

    def _build(self) -> None:
        """(Re)create the whole content; called again after a language change."""
        tabs = QTabWidget()
        user_tab = UnitTab(UserBackend(tabs), tabs)
        tabs.addTab(user_tab, tr("User services"))

        picker = QComboBox()
        picker.setToolTip(tr("Language"))
        for label, code in ((tr("System"), "system"), ("English", "en"), ("Italiano", "it")):
            picker.addItem(label, code)
        picker.setCurrentIndex(picker.findData(self._settings.value("language", "system")))
        picker.currentIndexChanged.connect(lambda _i: self._change_language(picker.currentData()))
        tabs.setCornerWidget(picker, Qt.Corner.TopRightCorner)

        self.setCentralWidget(tabs)  # deletes the previous content, backends included
        self.statusBar().showMessage(tr("Ready"))
        user_tab.message.connect(self.statusBar().showMessage)

    def _change_language(self, code: str) -> None:
        self._settings.setValue("language", code)
        set_language(code)
        QTimer.singleShot(0, self._build)  # not from inside the combo's own signal
