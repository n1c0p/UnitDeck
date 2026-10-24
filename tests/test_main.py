# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Nicola Palmieri (n1c0p)
import pytest

from unitdeck.__main__ import ensure_not_root


def test_root_is_refused(monkeypatch):
    monkeypatch.setattr("os.geteuid", lambda: 0)
    with pytest.raises(SystemExit):
        ensure_not_root()


def test_normal_user_is_accepted(monkeypatch):
    monkeypatch.setattr("os.geteuid", lambda: 1000)
    ensure_not_root()
