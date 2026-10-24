# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Nicola Palmieri (n1c0p)

from __future__ import annotations

from PyQt6.QtCore import QSettings, QTimer
from PyQt6.QtGui import QActionGroup
from PyQt6.QtWidgets import QMainWindow, QMenuBar, QMessageBox, QTabWidget

from unitdeck.backend.systemd import UserBackend
from unitdeck.gui.unit_tab import UnitTab
from unitdeck.gui.update_dialog import UpdateDialog
from unitdeck.i18n import set_language, tr
from unitdeck.updater import REPOSITORY, Release, Updater, is_dev_version

STARTUP_CHECK_DELAY_MS = 3000


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("UnitDeck")
        self.resize(1150, 650)
        self._settings = QSettings()
        set_language(self._settings.value("language", "system"))
        self._updater = Updater(self)
        self._updater.available.connect(self._on_update_available)
        self._updater.up_to_date.connect(self._on_up_to_date)
        self._updater.check_failed.connect(self._on_check_failed)
        self._manual_check = False
        self._build()
        if self.check_at_startup() and not is_dev_version(self._updater.installed):
            QTimer.singleShot(STARTUP_CHECK_DELAY_MS, self._updater.check)

    def check_at_startup(self) -> bool:
        return self._settings.value("check_updates", True, type=bool)

    # ---- construction (repeated after a language change) ----------------------------------

    def _build(self) -> None:
        tabs = QTabWidget()
        user_tab = UnitTab(UserBackend(tabs), tabs)
        tabs.addTab(user_tab, tr("User services"))
        self.setCentralWidget(tabs)  # deletes the previous content, backends included
        self.setMenuBar(self._menu_bar())
        self.statusBar().showMessage(tr("Ready"))
        user_tab.message.connect(self.statusBar().showMessage)

    def _menu_bar(self) -> QMenuBar:
        bar = QMenuBar()
        settings = bar.addMenu(tr("Settings"))
        language = settings.addMenu(tr("Language"))
        group = QActionGroup(language)
        current = self._settings.value("language", "system")
        for label, code in ((tr("System"), "system"), ("English", "en"), ("Italiano", "it")):
            action = language.addAction(label)
            action.setCheckable(True)
            action.setChecked(code == current)
            action.setData(code)
            group.addAction(action)
        group.triggered.connect(lambda action: self._change_language(action.data()))
        updates = settings.addAction(tr("Check for updates at startup"))
        updates.setCheckable(True)
        updates.setChecked(self.check_at_startup())
        updates.toggled.connect(lambda on: self._settings.setValue("check_updates", on))

        info = bar.addMenu(tr("Info"))
        info.addAction(tr("Check for updates…"), self._check_updates)
        info.addSeparator()
        info.addAction(tr("About UnitDeck…"), self._about)
        info.addAction(tr("About Qt…"), lambda: QMessageBox.aboutQt(self))
        return bar

    def _change_language(self, code: str) -> None:
        self._settings.setValue("language", code)
        set_language(code)
        QTimer.singleShot(0, self._build)  # not from inside the menu's own signal

    # ---- info menu --------------------------------------------------------------------------

    def _about(self) -> None:
        url = f"https://github.com/{REPOSITORY}"
        QMessageBox.about(
            self,
            tr("About UnitDeck"),
            f"<h3>UnitDeck</h3>"
            f"<p>{tr('Version {version}').format(version=self._updater.installed)}</p>"
            f"<p>{tr('A desktop application to manage systemd system and user services.')}</p>"
            f"<p>{tr('Licensed under the GNU GPL, version 3 or later.')}</p>"
            f'<p><a href="{url}">{url}</a></p>'
            "<p>Copyright © 2026 Nicola Palmieri (n1c0p)</p>",
        )

    def _check_updates(self) -> None:
        self._manual_check = True
        self.statusBar().showMessage(tr("Checking for updates…"))
        self._updater.check()

    def _on_update_available(self, release: Release) -> None:
        self._manual_check = False
        self.statusBar().showMessage(tr("Update available"))
        UpdateDialog(self._updater, release, self).show()

    def _on_up_to_date(self, _latest: str) -> None:
        message = tr("UnitDeck is up to date ({version}).").format(version=self._updater.installed)
        self.statusBar().showMessage(message)
        if self._manual_check:
            QMessageBox.information(self, "UnitDeck", message)
        self._manual_check = False

    def _on_check_failed(self, error: str) -> None:
        message = tr("Update check failed: {error}").format(error=error)
        self.statusBar().showMessage(message)
        if self._manual_check:
            QMessageBox.warning(self, "UnitDeck", message)
        self._manual_check = False
