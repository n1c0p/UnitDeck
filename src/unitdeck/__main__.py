# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Nicola Palmieri (n1c0p)
"""Entry point: ``python -m unitdeck`` or the ``unitdeck`` script."""

import sys
import traceback

from unitdeck import APP_ID, __version__
from unitdeck.rootcheck import ROOT_ERROR, ensure_not_root  # noqa: F401 - re-exported for tests


def report_exception(kind, value, tb) -> None:
    """An unhandled exception in a Qt slot would abort the process: show it instead."""
    text = "".join(traceback.format_exception(kind, value, tb))
    sys.stderr.write(text)
    try:
        from PyQt6.QtWidgets import QApplication, QMessageBox

        if QApplication.instance() is not None:
            box = QMessageBox(QMessageBox.Icon.Critical, "UnitDeck", str(value) or kind.__name__)
            box.setDetailedText(text)
            box.exec()
    except Exception:  # noqa: BLE001 - nothing else to do while reporting a crash
        pass


def main() -> None:
    if "--version" in sys.argv[1:]:
        print(f"UnitDeck {__version__}")
        return
    ensure_not_root()
    if "--check" in sys.argv[1:]:  # packaging smoke test: Qt and its plugins load, nothing shown
        import PyQt6.QtDBus  # noqa: F401
        import PyQt6.QtNetwork  # noqa: F401
        from PyQt6.QtWidgets import QApplication

        QApplication(sys.argv)
        print(f"UnitDeck {__version__}: Qt ok")
        return
    # Qt is imported only after the root check, so the check runs even if Qt is broken.
    from PyQt6.QtWidgets import QApplication

    from unitdeck.gui.main_window import MainWindow

    sys.excepthook = report_exception
    app = QApplication(sys.argv)
    app.setApplicationName("UnitDeck")
    app.setOrganizationName("UnitDeck")  # QSettings -> ~/.config/UnitDeck/UnitDeck.conf
    app.setApplicationVersion(__version__)
    app.setDesktopFileName(APP_ID)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
