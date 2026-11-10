# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Nicola Palmieri (n1c0p)
"""Regenerate the terminal-interface screenshots in docs/screenshots/ (SVG).

Runs the real unitdeck-tui headless on the test suite's fake D-Bus runtime with made-up
units, so no real service is read or touched:

    .venv/bin/python docs/screenshots.py
"""

from __future__ import annotations

import asyncio
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "screenshots"
sys.path.insert(0, str(ROOT / "tests"))

from fake_transport import FakeRuntime, FakeTransport  # noqa: E402

from unitdeck.backend import base  # noqa: E402
from unitdeck.tui.app import UnitDeckApp  # noqa: E402

SIZE = (120, 34)


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
        # after the screen has its size, or the log wraps at Textual's default 80 columns
        asyncio.get_running_loop().call_later(0.2, self._journal, on_line)
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


def make_app(own_dir: str) -> UnitDeckApp:
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
    app = UnitDeckApp(runtime_factory=lambda: runtime)
    app._tty_agent = False
    return app


async def shoot() -> None:
    from textual.widgets import DataTable, Static

    from unitdeck.tui.screens import EditScreen
    from unitdeck.tui.service_editor import Section, ServiceEditor

    OUT.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as own_dir:
        base.own_unit_dir = lambda scope: own_dir
        app = make_app(own_dir)
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


if __name__ == "__main__":
    asyncio.run(shoot())
    print("\n".join(sorted(str(p.relative_to(ROOT)) for p in OUT.glob("tui-*.svg"))))
