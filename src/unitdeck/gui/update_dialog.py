# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Nicola Palmieri (n1c0p)

from __future__ import annotations

from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from unitdeck.i18n import tr
from unitdeck.updater import Release, Updater


class UpdateDialog(QDialog):
    def __init__(self, updater: Updater, release: Release, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._updater = updater
        self._release = release
        self.setWindowTitle(tr("Update available"))
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.resize(560, 420)

        headline = QLabel(
            tr("UnitDeck {new} is available (installed: {old}).").format(
                new=release.version, old=updater.installed
            )
        )
        notes = QTextBrowser()
        notes.setOpenExternalLinks(True)
        notes.setMarkdown(release.notes or tr("No release notes."))
        self._progress = QProgressBar()
        self._progress.hide()
        self._status = QLabel()
        self._status.setWordWrap(True)

        self._install = QPushButton(tr("Download and install"))
        self._install.setEnabled(bool(release.deb_url))
        if not release.deb_url:
            self._status.setText(tr("No package for this system in the release."))
        page = QPushButton(tr("Open release page"))
        later = QPushButton(tr("Later"))
        buttons = QHBoxLayout()
        buttons.addWidget(page)
        buttons.addStretch(1)
        buttons.addWidget(later)
        buttons.addWidget(self._install)

        layout = QVBoxLayout(self)
        layout.addWidget(headline)
        layout.addWidget(notes, 1)
        layout.addWidget(self._progress)
        layout.addWidget(self._status)
        layout.addLayout(buttons)

        self._install.clicked.connect(self._start)
        page.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(release.page_url)))
        later.clicked.connect(self.reject)
        updater.progress.connect(self._on_progress)
        updater.downloaded.connect(self._on_downloaded)
        updater.download_failed.connect(self._on_download_failed)
        updater.install_finished.connect(self._on_installed)

    def _start(self) -> None:
        self._install.setEnabled(False)
        self._progress.show()
        self._status.setText(tr("Downloading…"))
        self._updater.download(self._release)

    def _on_progress(self, received: int, total: int) -> None:
        self._progress.setMaximum(max(total, 0))
        self._progress.setValue(received)

    def _on_downloaded(self, path: str) -> None:
        self._progress.hide()
        self._status.setText(tr("Installing… the system will ask for your password."))
        self._updater.install(path)

    def _on_download_failed(self, error: str) -> None:
        self._progress.hide()
        self._install.setEnabled(True)
        if error == "checksum mismatch":
            error = tr("Checksum mismatch, the downloaded file was discarded.")
        self._status.setText(tr("Download failed: {error}").format(error=error))

    def _on_installed(self, ok: bool, output: str) -> None:
        if ok:
            self._status.setText(tr("Installed. Restart UnitDeck to use the new version."))
            return
        self._install.setEnabled(True)
        self._status.setText(tr("Installation failed."))
        box = QMessageBox(
            QMessageBox.Icon.Warning, "UnitDeck", tr("Installation failed."), parent=self
        )
        box.setDetailedText(output)
        box.exec()
