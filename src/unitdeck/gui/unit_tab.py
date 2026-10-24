# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Nicola Palmieri (n1c0p)
"""One tab: search bar, filters, unit table with per-row actions, context menu and shortcuts."""

from __future__ import annotations

from PyQt6.QtCore import QModelIndex, QPoint, Qt, pyqtSignal
from PyQt6.QtGui import QCursor, QIcon, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPushButton,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from unitdeck.backend.base import SystemdBackend, Unit
from unitdeck.gui.actions_delegate import ActionsDelegate
from unitdeck.gui.log_viewer import LogViewer
from unitdeck.i18n import tr
from unitdeck.model import (
    ACTIONS,
    DESCRIPTION,
    FILTER_LABELS,
    NAME,
    UnitModel,
    UnitProxy,
    UnitRole,
)

ACTION_LABELS = {  # source strings, translate with tr() at use time
    "start": "Start",
    "stop": "Stop",
    "restart": "Restart",
    "reload": "Reload",
    "enable": "Enable at boot",
    "disable": "Disable at boot",
    "mask": "Mask",
    "unmask": "Unmask",
    "reset-failed": "Reset failed state",
    "logs": "Show logs",
    "daemon-reload": "Reload configuration",
    "refresh": "Refresh unit list",
    "details": "Read details",
}
SHORTCUTS = {"start": "Ctrl+S", "stop": "Ctrl+T", "restart": "Ctrl+R", "logs": "Ctrl+L"}
JOB_RESULTS = {  # systemd job results other than "done"
    "failed": "the service failed, check its logs",
    "timeout": "timed out",
    "canceled": "operation cancelled",
    "dependency": "a dependency failed",
    "skipped": "operation skipped (condition not met)",
    "invalid": "operation not valid in the current state",
    "assert": "unit assertion not met",
    "unsupported": "operation not supported",
}
SERVICE_RESULTS = {  # Result property of a failed service
    "start-limit-hit": "start requests repeated too quickly, wait ten seconds and start it again",
    "exit-code": "the process exited with an error code, check its logs",
    "signal": "the process was killed by a signal, check its logs",
    "core-dump": "the process crashed (core dump), check its logs",
    "timeout": "the process did not start or stop within the timeout",
    "watchdog": "the watchdog timeout was hit",
    "oom-kill": "the process was killed for lack of memory",
    "resources": "a resource limit could not be applied",
    "protocol": "the service did not follow the notification protocol",
}
AUTH_ERRORS = (  # polkit dialog cancelled or password refused: status bar only, no popup
    "org.freedesktop.DBus.Error.AccessDenied",
    "org.freedesktop.DBus.Error.InteractiveAuthorizationRequired",
)
ERROR_LABELS = {  # D-Bus error names
    AUTH_ERRORS[0]: "authorization denied",
    AUTH_ERRORS[1]: "authorization required",
    "org.freedesktop.DBus.Error.NoReply": "systemd did not answer in time",
    "org.freedesktop.systemd1.NoSuchUnit": "unit not found",
    "org.freedesktop.systemd1.UnitMasked": "the unit is masked",
    "org.freedesktop.systemd1.JobTypeNotApplicable": "operation not applicable to this unit",
}


def readable(detail: str) -> str:
    """Human-readable, translated reason for a failed operation."""
    if detail in JOB_RESULTS:
        return tr(JOB_RESULTS[detail])
    if detail.startswith("failed (") and detail.endswith(")"):
        result = detail[8:-1]
        return (
            tr(SERVICE_RESULTS[result])
            if result in SERVICE_RESULTS
            else f"{tr(JOB_RESULTS['failed'])} ({result})"
        )
    name, _, message = detail.partition(": ")
    if name in ERROR_LABELS:
        return tr(ERROR_LABELS[name])
    return message or detail


class UnitTab(QWidget):
    message = pyqtSignal(str)  # for the status bar

    def __init__(self, backend: SystemdBackend, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._backend = backend
        self._model = UnitModel(backend, self)
        self._proxy = UnitProxy(backend.own_dir, self)
        self._proxy.setSourceModel(self._model)
        self._logs: dict[str, LogViewer] = {}

        search = QLineEdit()
        search.setPlaceholderText(tr("Search by name or description…"))
        search.setClearButtonEnabled(True)
        search.textChanged.connect(self._proxy.set_text)
        state = QComboBox()
        for value, label in FILTER_LABELS.items():
            state.addItem(tr(label), value)
        state.currentIndexChanged.connect(lambda _i: self._proxy.set_state(state.currentData()))
        reload = QPushButton(QIcon.fromTheme("view-refresh-symbolic"), tr("Reload configuration"))
        reload.setToolTip(tr("daemon-reload: re-read unit files changed on disk"))
        reload.clicked.connect(backend.daemon_reload)
        refresh = QPushButton(tr("Refresh"))
        refresh.setToolTip(tr("Re-read the unit list"))
        refresh.clicked.connect(backend.refresh)
        top = QHBoxLayout()
        top.addWidget(search, 1)
        top.addWidget(state)
        top.addWidget(reload)
        top.addWidget(refresh)

        self._table = QTableView()
        self._table.setModel(self._proxy)
        self._table.setSortingEnabled(True)
        self._table.sortByColumn(NAME, Qt.SortOrder.AscendingOrder)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.setShowGrid(False)
        self._table.setWordWrap(False)
        self._table.verticalHeader().hide()
        self._delegate = ActionsDelegate(self._table)
        self._table.setItemDelegateForColumn(ACTIONS, self._delegate)
        header = self._table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(NAME, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(DESCRIPTION, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(ACTIONS, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(NAME, 280)
        header.resizeSection(ACTIONS, self._delegate.sizeHint(None, QModelIndex()).width())
        self._table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._table.customContextMenuRequested.connect(self._context_menu)
        self._table.doubleClicked.connect(lambda index: self._run("logs", index.data(UnitRole)))
        self._delegate.triggered.connect(self._on_button)
        for action, keys in SHORTCUTS.items():
            shortcut = QShortcut(QKeySequence(keys), self._table)
            shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
            shortcut.setAutoRepeat(False)  # a held key must not queue one action per repeat
            shortcut.activated.connect(lambda a=action: self._run_selected(a))

        layout = QVBoxLayout(self)
        layout.addLayout(top)
        layout.addWidget(self._table)

        backend.operation_finished.connect(self._on_finished)
        backend.busy_changed.connect(lambda *_: self._delegate.set_spinning(bool(backend.busy)))
        backend.refresh()

    # ---- actions ----------------------------------------------------------------------------

    def selected_unit(self) -> Unit | None:
        index = self._table.currentIndex()
        return index.data(UnitRole) if index.isValid() else None

    def _run_selected(self, action: str) -> None:
        unit = self.selected_unit()
        if unit is not None and unit.can(action) and unit.name not in self._backend.busy:
            self._run(action, unit)

    def _on_button(self, action: str, index: QModelIndex) -> None:
        unit = index.data(UnitRole)
        if action == "more":
            self._table.setCurrentIndex(index)
            self._show_menu(unit, QCursor.pos())
        else:
            self._run(action, unit)

    def _run(self, action: str, unit: Unit) -> None:
        if action == "logs":
            self._show_logs(unit)
            return
        self.message.emit(
            tr("{action} {unit}…").format(action=tr(ACTION_LABELS[action]), unit=unit.name)
        )
        self._backend.run(action, unit.name)

    def _show_logs(self, unit: Unit) -> None:
        viewer = self._logs.get(unit.name)
        if viewer is None:
            viewer = LogViewer(unit.name, self._backend.scope, self)
            viewer.destroyed.connect(lambda _obj=None, n=unit.name: self._logs.pop(n, None))
            self._logs[unit.name] = viewer
        viewer.show()
        viewer.raise_()
        viewer.activateWindow()

    def _context_menu(self, pos: QPoint) -> None:
        index = self._table.indexAt(pos)
        if index.isValid():
            self._table.setCurrentIndex(index)
            self._show_menu(index.data(UnitRole), self._table.viewport().mapToGlobal(pos))

    def _show_menu(self, unit: Unit, global_pos: QPoint) -> None:
        menu = QMenu(self)
        busy = unit.name in self._backend.busy

        def add(action: str):
            entry = menu.addAction(tr(ACTION_LABELS[action]))
            entry.setEnabled(not busy and unit.can(action))
            entry.triggered.connect(lambda _checked=False, a=action: self._run(a, unit))
            return entry

        add("start")
        add("stop")
        add("restart")
        reload = add("reload")
        if unit.can("reset-failed"):
            add("reset-failed")
        menu.addSeparator()
        add("disable" if unit.can("disable") else "enable")
        add("unmask" if unit.masked else "mask")
        menu.addSeparator()
        add("logs")
        if unit.loaded and unit.can_reload is None:
            # CanReload is fetched lazily; the entry turns on when the answer arrives.
            def update(name: str) -> None:
                current = self._backend.units.get(name)
                if name == unit.name and current is not None:
                    reload.setEnabled(not busy and current.can("reload"))

            self._backend.unit_updated.connect(update)
            menu.aboutToHide.connect(lambda: self._backend.unit_updated.disconnect(update))
            self._backend.fetch_details(unit.name)
        menu.exec(global_pos)

    # ---- results ----------------------------------------------------------------------------

    def _on_finished(self, name: str, action: str, ok: bool, detail: str) -> None:
        words = {"action": tr(ACTION_LABELS.get(action, action)), "unit": name}
        if ok:
            self.message.emit(tr("{action} {unit}: done").format(**words).replace("  ", " "))
            return
        words["reason"] = readable(detail)
        self.message.emit(tr("{action} {unit}: {reason}").format(**words).replace("  ", " "))
        if action in ("refresh", "details") or detail.partition(": ")[0] in AUTH_ERRORS:
            return
        box = QMessageBox(
            QMessageBox.Icon.Warning,
            "UnitDeck",
            tr("{action} {unit} failed:\n{reason}").format(**words).replace("  ", " "),
            QMessageBox.StandardButton.Ok,
            self,
        )
        box.setDetailedText(detail)  # the original systemd / D-Bus message
        box.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        box.show()  # non-modal: the table keeps updating meanwhile
