# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Nicola Palmieri (n1c0p)
"""Qt models: the unit table and its search / state filter proxy."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from PyQt6.QtCore import QAbstractTableModel, QModelIndex, QObject, QSortFilterProxyModel, Qt
from PyQt6.QtGui import QColor

from unitdeck.backend.base import SystemdBackend, Unit
from unitdeck.i18n import tr

COLUMNS = ("Name", "Description", "Load", "State", "Startup", "Actions")  # source strings
NAME, DESCRIPTION, LOAD, ACTIVE, STARTUP, ACTIONS = range(len(COLUMNS))

UnitRole = Qt.ItemDataRole.UserRole + 1
BusyRole = Qt.ItemDataRole.UserRole + 2

STATE_COLORS = {"active": QColor("#2da44e"), "failed": QColor("#d1242f")}


class UnitModel(QAbstractTableModel):
    def __init__(self, backend: SystemdBackend, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._backend = backend
        self._rows: list[Unit] = []
        self._row_of: dict[str, int] = {}
        backend.units_changed.connect(self._reload)
        backend.unit_updated.connect(self._row_changed)
        backend.busy_changed.connect(lambda name, _busy: self._row_changed(name))

    def rowCount(self, parent: QModelIndex | None = None) -> int:
        return 0 if parent is not None and parent.isValid() else len(self._rows)

    def columnCount(self, parent: QModelIndex | None = None) -> int:
        return len(COLUMNS)

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = 0) -> Any:
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return tr(COLUMNS[section])
        return None

    def data(self, index: QModelIndex, role: int = 0) -> Any:
        unit = self._rows[index.row()]
        if role == UnitRole:
            return unit
        if role == BusyRole:
            return unit.name in self._backend.busy
        column = index.column()
        if role == Qt.ItemDataRole.DisplayRole:
            match column:
                case 0:
                    return unit.name
                case 1:
                    return unit.description
                case 2:
                    return unit.load_state or tr("not loaded")
                case 3:
                    return f"{unit.active_state} ({unit.sub_state})" if unit.loaded else "inactive"
                case 4:
                    return unit.unit_file_state or "–"
        elif role == Qt.ItemDataRole.ForegroundRole and column == ACTIVE:
            return STATE_COLORS.get(unit.active_state, QColor(Qt.GlobalColor.gray))
        elif role == Qt.ItemDataRole.ToolTipRole and column == NAME:
            return unit.fragment_path or None
        return None

    def _reload(self) -> None:
        rows = sorted(self._backend.units.values(), key=lambda u: u.name)
        names = [u.name for u in rows]
        if names == list(self._row_of):  # same units: update in place, keep selection and scroll
            self._rows = rows
            if rows:
                self.dataChanged.emit(self.index(0, 0), self.index(len(rows) - 1, len(COLUMNS) - 1))
            return
        self.beginResetModel()
        self._rows = rows
        self._row_of = {name: i for i, name in enumerate(names)}
        self.endResetModel()

    def _row_changed(self, name: str) -> None:
        row = self._row_of.get(name)
        if row is not None:
            self.dataChanged.emit(self.index(row, 0), self.index(row, len(COLUMNS) - 1))


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


class UnitProxy(QSortFilterProxyModel):
    """Search on name/description plus a state filter; sorting is the default string sort."""

    def __init__(self, own_dir: str, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._own_dir = own_dir.rstrip("/") + "/"
        self._text = ""
        self.state = StateFilter.ALL
        self.setSortCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)

    def set_text(self, text: str) -> None:
        self._text = text.strip().lower()
        self.invalidateRowsFilter()

    def set_state(self, state: StateFilter) -> None:
        self.state = state
        self.invalidateRowsFilter()

    def filterAcceptsRow(self, row: int, parent: QModelIndex) -> bool:
        unit: Unit = self.sourceModel().index(row, NAME, parent).data(UnitRole)
        if (
            self._text
            and self._text not in unit.name.lower()
            and (self._text not in unit.description.lower())
        ):
            return False
        match self.state:
            case StateFilter.ACTIVE:
                return unit.active_state == "active"
            case StateFilter.INACTIVE:
                return unit.active_state == "inactive"
            case StateFilter.FAILED:
                return unit.active_state == "failed"
            case StateFilter.MINE:
                return unit.fragment_path.startswith(self._own_dir)
        return True
