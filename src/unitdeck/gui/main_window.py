# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Nicola (n1c0p)

from __future__ import annotations

from PyQt6.QtWidgets import QMainWindow, QTabWidget

from unitdeck.backend.systemd import UserBackend
from unitdeck.gui.unit_tab import UnitTab


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("UnitDeck")
        self.resize(1150, 650)
        tabs = QTabWidget()
        user_tab = UnitTab(UserBackend(self))
        tabs.addTab(user_tab, "Servizi utente")
        self.setCentralWidget(tabs)
        self.statusBar().showMessage("Pronto")
        user_tab.message.connect(self.statusBar().showMessage)
