# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Nicola Palmieri (n1c0p)
"""The desktop dialogs' verify: closing the dialog while it runs must not crash (#63)."""

import os
from types import SimpleNamespace

from PyQt6 import sip
from PyQt6.QtCore import QObject

from unitdeck.backend import unitfiles
from unitdeck.backend.base import Scope
from unitdeck.gui.verify import verify


class SlowRuntime:
    """systemd-analyze that has not answered yet: the test finishes it with ``finish()``."""

    def __init__(self) -> None:
        self.argv: list[str] = []
        self._done = None

    def run(self, argv, stdin, on_done) -> None:
        self.argv, self._done = argv, on_done

    def finish(self, code: int, out: str) -> None:
        self._done(code, out, "")


def start(runtime: SlowRuntime, owner: QObject, results: list) -> str:
    staged = unitfiles.stage_for_verify("x.service", "[Service]\nExecStart=/bin/true\n")
    backend = SimpleNamespace(scope=Scope.USER, runtime=runtime)
    verify(owner, backend, staged, lambda code, lines: results.append((code, lines)))
    return staged


def test_result_reaches_the_dialog_and_staging_is_removed():
    runtime, owner, results = SlowRuntime(), QObject(), []
    staged = start(runtime, owner, results)
    assert runtime.argv == ["systemd-analyze", "verify", "--man=no", "--user", staged]
    runtime.finish(1, f"{staged}:2: Unknown key name 'Restrat'.\nother.service: noise\n")
    assert results == [(1, "x.service:2: Unknown key name 'Restrat'.")]
    assert not os.path.exists(os.path.dirname(staged))


def test_closed_dialog_is_left_alone_but_staging_is_removed():
    runtime, owner, results = SlowRuntime(), QObject(), []
    staged = start(runtime, owner, results)
    sip.delete(owner)  # the dialog closed and was deleted while the check ran
    runtime.finish(0, "")
    assert results == []
    assert not os.path.exists(os.path.dirname(staged))
