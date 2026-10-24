# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Nicola (n1c0p)
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
from unitdeck.model import (
    ACTIONS,
    DESCRIPTION,
    FILTER_LABELS,
    NAME,
    UnitModel,
    UnitProxy,
    UnitRole,
)

ACTION_LABELS = {
    "start": "Avvia",
    "stop": "Ferma",
    "restart": "Riavvia",
    "reload": "Ricarica",
    "enable": "Abilita all'avvio",
    "disable": "Disabilita all'avvio",
    "mask": "Maschera",
    "unmask": "Smaschera",
    "logs": "Mostra log",
    "daemon-reload": "Ricarica configurazione",
    "refresh": "Aggiornamento elenco",
    "details": "Lettura dettagli",
}
SHORTCUTS = {"start": "Ctrl+S", "stop": "Ctrl+T", "restart": "Ctrl+R", "logs": "Ctrl+L"}
JOB_RESULTS = {  # systemd job results other than "done"
    "failed": "il servizio ha fallito, controlla i log",
    "timeout": "tempo scaduto",
    "canceled": "operazione annullata",
    "dependency": "una dipendenza ha fallito",
    "skipped": "operazione saltata (condizione non soddisfatta)",
    "invalid": "operazione non valida per lo stato attuale",
    "assert": "asserzione della unit non soddisfatta",
    "unsupported": "operazione non supportata",
}
ERROR_LABELS = {  # D-Bus error names
    "org.freedesktop.DBus.Error.AccessDenied": "autorizzazione negata",
    "org.freedesktop.DBus.Error.InteractiveAuthorizationRequired": "autorizzazione richiesta",
    "org.freedesktop.DBus.Error.NoReply": "systemd non ha risposto in tempo",
    "org.freedesktop.systemd1.NoSuchUnit": "unit non trovata",
    "org.freedesktop.systemd1.UnitMasked": "la unit è mascherata",
    "org.freedesktop.systemd1.JobTypeNotApplicable": "operazione non applicabile a questa unit",
}


def readable(detail: str) -> str:
    if detail in JOB_RESULTS:
        return JOB_RESULTS[detail]
    name, _, message = detail.partition(": ")
    return ERROR_LABELS.get(name, message or detail)


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
        search.setPlaceholderText("Cerca per nome o descrizione…")
        search.setClearButtonEnabled(True)
        search.textChanged.connect(self._proxy.set_text)
        state = QComboBox()
        for value, label in FILTER_LABELS.items():
            state.addItem(label, value)
        state.currentIndexChanged.connect(lambda _i: self._proxy.set_state(state.currentData()))
        reload = QPushButton(QIcon.fromTheme("view-refresh-symbolic"), "Ricarica configurazione")
        reload.setToolTip("daemon-reload: rilegge i file unit modificati su disco")
        reload.clicked.connect(backend.daemon_reload)
        refresh = QPushButton("Aggiorna")
        refresh.setToolTip("Rilegge l'elenco delle unit")
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
        self.message.emit(f"{ACTION_LABELS[action]} {unit.name}…")
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
            entry = menu.addAction(ACTION_LABELS[action])
            entry.setEnabled(not busy and unit.can(action))
            entry.triggered.connect(lambda _checked=False, a=action: self._run(a, unit))
            return entry

        add("start")
        add("stop")
        add("restart")
        reload = add("reload")
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
        label = ACTION_LABELS.get(action, action)
        target = f" {name}" if name else ""
        if ok:
            self.message.emit(f"{label}{target}: completato")
            return
        reason = readable(detail)
        self.message.emit(f"{label}{target}: {reason}")
        if action in ("refresh", "details"):
            return
        box = QMessageBox(
            QMessageBox.Icon.Warning,
            "UnitDeck",
            f"{label}{target} non riuscito:\n{reason}",
            QMessageBox.StandardButton.Ok,
            self,
        )
        box.setDetailedText(detail)  # the original systemd / D-Bus message
        box.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        box.show()  # non-modal: the table keeps updating meanwhile
