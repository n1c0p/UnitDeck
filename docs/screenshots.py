# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Nicola Palmieri (n1c0p)
"""Regenerate the screenshots: docs/screenshot.png and docs/screenshots/ (gui-*.png, tui-*.svg).

Runs the real applications without a screen (Qt offscreen, Textual headless) on the test
suite's fake D-Bus runtime with made-up units: no real service or setting is read or changed,
and nothing is written outside a temporary directory (the wizard's systemd-analyze verify
only reads a staged copy):

    .venv/bin/python docs/screenshots.py
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "screenshots"
sys.path.insert(0, str(ROOT / "tests"))

from fake_transport import FakeRuntime, FakeTransport  # noqa: E402

from unitdeck.backend import base  # noqa: E402
from unitdeck.tui.app import UnitDeckApp  # noqa: E402

SIZE = (120, 34)  # terminal, columns x rows
WINDOW = (1280, 560)  # desktop window, logical pixels (saved at 1.5x)


def unit(name, description, active, sub, load="loaded"):
    return (name, description, load, active, sub, "", f"/u/{name}", 0, "", "/")


SYSTEM = [
    unit("bluetooth.service", "Bluetooth service", "active", "running"),
    unit("cron.service", "Regular background program processing daemon", "active", "running"),
    unit("cups.service", "CUPS Scheduler", "active", "running"),
    unit("docker.service", "Docker Application Container Engine", "inactive", "dead"),
    unit("nginx.service", "A high performance web server", "failed", "failed"),
    unit("NetworkManager.service", "Network Manager", "active", "running"),
    unit("postgresql.service", "PostgreSQL RDBMS", "active", "exited"),
    unit("ssh.service", "OpenBSD Secure Shell server", "active", "running"),
    unit("systemd-journald.service", "Journal Service", "active", "running"),
    unit("systemd-timesyncd.service", "Network Time Synchronization", "active", "running"),
    unit("ufw.service", "Uncomplicated firewall", "active", "exited"),
]
SYSTEM_FILES = [
    ("/usr/lib/systemd/system/bluetooth.service", "enabled"),
    ("/usr/lib/systemd/system/cron.service", "enabled"),
    ("/usr/lib/systemd/system/cups.service", "enabled"),
    ("/usr/lib/systemd/system/docker.service", "disabled"),
    ("/usr/lib/systemd/system/nginx.service", "enabled"),
    ("/usr/lib/systemd/system/NetworkManager.service", "enabled"),
    ("/usr/lib/systemd/system/postgresql.service", "enabled"),
    ("/usr/lib/systemd/system/ssh.service", "enabled"),
    ("/usr/lib/systemd/system/systemd-journald.service", "static"),
    ("/usr/lib/systemd/system/systemd-timesyncd.service", "enabled"),
    ("/usr/lib/systemd/system/ufw.service", "enabled"),
]
BACKUP = """\
# Nightly copy of ~/Documents to the NAS
[Unit]
Description=Backup of my documents
After=network-online.target

[Service]
Type=oneshot
ExecStart=/usr/bin/rsync -a %h/Documents/ /mnt/nas/backup/
Restrat=on-failure
Nice=10

[Install]
WantedBy=default.target
"""
JOURNAL = [
    (6, "nginx", "Starting nginx.service - A high performance web server..."),
    (3, "nginx", 'nginx: [emerg] unknown directive "proxy_pas" in /etc/nginx/sites-enabled/app:14'),
    (3, "nginx", "nginx: configuration file /etc/nginx/nginx.conf test failed"),
    (4, "systemd", "nginx.service: Control process exited, code=exited, status=1/FAILURE"),
    (4, "systemd", "nginx.service: Failed with result 'exit-code'."),
    (3, "systemd", "Failed to start nginx.service - A high performance web server."),
]


class DemoRuntime(FakeRuntime):
    def __init__(self, system: FakeTransport, user: FakeTransport) -> None:
        super().__init__(system)
        self._user = user

    def transport(self, bus: str, interactive: bool = False):
        return self._transport if bus == "system" else self._user

    def stream(self, argv, on_line, on_exit):
        try:  # Textual: after the screen has its size, or the log wraps at 80 columns
            asyncio.get_running_loop().call_later(0.2, self._journal, on_line)
        except RuntimeError:  # Qt: no asyncio loop, the viewer takes the lines at once
            self._journal(on_line)
        return lambda: None

    @staticmethod
    def _journal(on_line) -> None:
        stamp = 1_794_326_400_000_000  # 2026-11-10 16:00 UTC
        for i, (priority, ident, message) in enumerate(JOURNAL):
            entry = {
                "__REALTIME_TIMESTAMP": str(stamp + i * 1_200_000),
                "PRIORITY": str(priority),
                "SYSLOG_IDENTIFIER": ident,
                "MESSAGE": message,
            }
            on_line(json.dumps(entry).encode())


def make_runtime(own_dir: str) -> DemoRuntime:
    backup = Path(own_dir) / "backup.service"
    backup.write_text(BACKUP)
    system = FakeTransport(
        {
            "ListUnits": [SYSTEM],
            "ListUnitFiles": [SYSTEM_FILES],
            "GetUser": ["/org/freedesktop/login1/user/_1000"],
            "Get": [True],
            "GetAll": [{}],
        }
    )
    user = FakeTransport(
        {
            "ListUnits": [[unit("backup.service", "Backup of my documents", "inactive", "dead")]],
            "ListUnitFiles": [[(str(backup), "enabled")]],
            "GetAll": [{}],
        }
    )
    runtime = DemoRuntime(system, user)
    runtime.own_dir = own_dir
    return runtime


async def shoot_tui(own_dir: str) -> None:
    from textual.widgets import DataTable, Static

    from unitdeck.tui.screens import EditScreen
    from unitdeck.tui.service_editor import Section, ServiceEditor

    runtime = make_runtime(own_dir)
    app = UnitDeckApp(runtime_factory=lambda: runtime)
    app._tty_agent = False
    async with app.run_test(size=SIZE) as pilot:
        app.console.width = SIZE[0]  # headless Rich measures text at 80 columns

        async def save(name: str) -> None:
            await pilot.pause()
            app.save_screenshot(f"tui-{name}.svg", str(OUT))

        # system services, the failed nginx selected
        await pilot.pause()
        app.sub_title = ""  # no version number: it would go stale
        app.pane.query_one(DataTable).focus()
        while app.pane.selected_name() != "nginx.service":
            await pilot.press("down")
        await save("units")
        # its journal
        await pilot.press("l")
        await pilot.pause(0.5)
        await save("logs")
        await pilot.press("escape")
        # user tab: the service editor on a unit of one's own, a typo flagged
        app.query_one("#scopes").active = "user"
        await pilot.pause()
        await pilot.press("slash", *"backup", "enter")
        await pilot.press("ctrl+e")
        await pilot.pause()
        assert isinstance(app.screen, EditScreen)
        info = app.screen.query_one("#info", Static)
        info.update(str(info.content).replace(own_dir, "~/.config/systemd/user"))
        editor = app.screen.query_one(ServiceEditor)
        service = next(s for s in editor.query(Section) if s.section == "Service")
        next(r for r in service.row_list() if r.directive.key == "Restrat").focus_field()
        await save("editor")
        # what a directive is for
        next(r for r in service.row_list() if r.directive.key == "Type").focus_field()
        await pilot.press("f1")
        await save("info")
        await pilot.press("escape", "escape")
        # new service from a template
        await pilot.press("n")
        await pilot.pause()
        app.screen.query_one("#name").value = "sync-photos"
        await save("new-service")


def shoot_gui(own_dir: str) -> None:
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    os.environ["QT_SCALE_FACTOR"] = "1.5"
    from PyQt6.QtCore import QSettings
    from PyQt6.QtGui import QIcon
    from PyQt6.QtTest import QTest
    from PyQt6.QtWidgets import QApplication

    from unitdeck.model import UnitRole

    # settings in the temporary directory, never the user's own ~/.config/UnitDeck
    QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, own_dir)
    app = QApplication(["unitdeck"])
    app.setOrganizationName("UnitDeck")
    app.setApplicationName("UnitDeck")
    app.setStyle("Fusion")  # same look on any machine; offscreen has no platform theme
    QIcon.setThemeName("Adwaita")
    settings = QSettings()
    settings.setValue("language", "en")
    settings.setValue("check_updates", False)

    from unitdeck.gui import main_window
    from unitdeck.gui.edit_dialog import EditDialog
    from unitdeck.gui.log_viewer import LogViewer
    from unitdeck.gui.new_service_wizard import NewServiceWizard

    runtime = make_runtime(own_dir)
    main_window.QtRuntime = lambda parent: runtime

    def save(widget, path: Path) -> None:
        widget.show()
        QTest.qWait(300)
        widget.grab().save(str(path))

    def unit_of(tab, name: str):
        table = tab._table
        for row in range(table.model().rowCount()):
            index = table.model().index(row, 0)
            if index.data(UnitRole).name == name:
                table.selectRow(row)
                return index.data(UnitRole)
        raise LookupError(name)

    def edit(tab, unit, where: str) -> EditDialog:
        dialog = EditDialog(tab._backend, unit, window)
        dialog.resize(1150, 600)
        dialog._info.setText(dialog._info.text().replace(own_dir, where))
        return dialog

    window = main_window.MainWindow()
    window.resize(*WINDOW)
    tabs = window.centralWidget()
    system_tab, user_tab = tabs.widget(0), tabs.widget(1)
    window.show()
    QTest.qWait(300)
    nginx = unit_of(system_tab, "nginx.service")
    save(window, ROOT / "docs" / "screenshot.png")

    # the failed nginx: its journal, then a drop-in for it
    logs = LogViewer(nginx.name, system_tab._backend.scope, runtime, window)
    logs.resize(1000, 330)
    save(logs, OUT / "gui-logs.png")
    logs.close()
    dropin = edit(system_tab, nginx, "/etc/systemd/system")
    text = dropin._editor.toPlainText()
    dropin._editor.setPlainText(text + "Restart=on-failure\nRestartSec=5s\n")
    save(dropin, OUT / "gui-dropin.png")
    dropin.reject()

    # a unit of one's own: edited directly, a typo flagged
    tabs.setCurrentIndex(1)
    backup = unit_of(user_tab, "backup.service")
    editor = edit(user_tab, backup, "~/.config/systemd/user")
    save(editor, OUT / "gui-editor.png")
    editor.reject()

    # new service from a template, ExecStart= filled in and verified
    wizard = NewServiceWizard(user_tab._backend, window)
    wizard.setField("name", "sync-photos")
    wizard.show()
    while wizard.currentId() < 2:
        wizard.next()
    page = wizard.currentPage()
    text = page._editor.toPlainText()
    page._editor.setPlainText(
        text.replace("ExecStart=\n", "ExecStart=/usr/bin/rsync -a %h/Pictures/ /mnt/nas/photos/\n")
    )
    page.verify()
    QTest.qWait(1500)
    save(wizard, OUT / "gui-new-service.png")
    wizard.reject()
    window.close()


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as own_dir:
        base.own_unit_dir = lambda scope: own_dir
        asyncio.run(shoot_tui(own_dir))
        shoot_gui(own_dir)
    shots = [ROOT / "docs" / "screenshot.png", *sorted(OUT.iterdir())]
    print("\n".join(str(p.relative_to(ROOT)) for p in shots))
