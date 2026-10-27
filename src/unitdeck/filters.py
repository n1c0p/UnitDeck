# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Nicola Palmieri (n1c0p)
"""State filter of the unit list, shared by both interfaces."""

from __future__ import annotations

from enum import StrEnum

from unitdeck.backend.base import Unit


class StateFilter(StrEnum):
    ALL = "all"
    ACTIVE = "active"
    INACTIVE = "inactive"
    FAILED = "failed"
    MINE = "mine"


FILTER_LABELS = {  # source strings, translate with tr() at use time
    StateFilter.ALL: "All",
    StateFilter.ACTIVE: "Active",
    StateFilter.INACTIVE: "Inactive",
    StateFilter.FAILED: "Failed",
    StateFilter.MINE: "Created by me",
}


def accepts(unit: Unit, text: str, state: StateFilter, own_dir: str) -> bool:
    """Text matches name or description (lower-case); the state filter keeps transitions visible."""
    if text and text not in unit.name.lower() and text not in unit.description.lower():
        return False
    match state:
        case StateFilter.ACTIVE:
            return unit.active_state not in ("inactive", "failed")
        case StateFilter.INACTIVE:
            return unit.active_state == "inactive"
        case StateFilter.FAILED:
            return unit.active_state == "failed"
        case StateFilter.MINE:
            return unit.fragment_path.startswith(own_dir.rstrip("/") + "/")
    return True
