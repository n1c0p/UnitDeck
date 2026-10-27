# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Nicola Palmieri (n1c0p)
from fake_transport import FakeRuntime

from unitdeck.backend.base import Scope
from unitdeck.backend.journal import JournalReader, format_entry, journalctl_args


def test_journalctl_args():
    assert journalctl_args("a.service", Scope.USER, 100, 4, True) == [
        "--no-pager",
        "-o",
        "json",
        "-u",
        "a.service",
        "-n",
        "100",
        "-p",
        "4",
        "--user",
        "-f",
    ]
    assert "--user" not in journalctl_args("a.service", Scope.SYSTEM, 10, 7, False)


def test_format_entry():
    line, priority = format_entry(
        {
            "__REALTIME_TIMESTAMP": "0",
            "PRIORITY": "3",
            "SYSLOG_IDENTIFIER": "app",
            "MESSAGE": "boom",
        }
    )
    assert line.endswith(" app: boom") and priority == 3
    line, priority = format_entry({"MESSAGE": [104, 105, 255], "_COMM": "x"})
    assert line.endswith(" x: hi�") and priority == 6
    assert format_entry({})[0].endswith("????-??-?? ??:??:?? ")


def test_reader_runs_journalctl_through_the_runtime():
    runtime = FakeRuntime()
    reader = JournalReader(runtime)
    entries = []
    reader.entry.connect(lambda line, priority: entries.append((line, priority)))
    reader.start("a.service", Scope.USER, 10, 7, False)
    assert runtime.processes[-1][0][:4] == ["journalctl", "--no-pager", "-o", "json"]
    reader._on_line(b'{"PRIORITY": "4", "MESSAGE": "hey", "SYSLOG_IDENTIFIER": "x"}')
    reader._on_line(b"not json")
    assert len(entries) == 1 and entries[0][1] == 4 and entries[0][0].endswith("x: hey")
