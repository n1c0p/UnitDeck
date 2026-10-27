# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Nicola Palmieri (n1c0p)
"""The one rule both interfaces share before anything else: never run as root."""

from __future__ import annotations

import os
import sys

ROOT_ERROR = (
    "UnitDeck must not run as root.\n"
    "Run it as a normal user: privileged actions are authorized through polkit."
)


def ensure_not_root() -> None:
    """Exit immediately when running as root. There is no way to bypass this."""
    if os.geteuid() == 0:
        sys.exit(ROOT_ERROR)
