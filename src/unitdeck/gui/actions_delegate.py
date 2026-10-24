# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Nicola Palmieri (n1c0p)
"""Action buttons painted in the "Azioni" column: no widget per row, fast on hundreds of units."""

from __future__ import annotations

from PyQt6.QtCore import QEvent, QModelIndex, QObject, QRect, QSize, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QHelpEvent, QIcon, QMouseEvent, QPainter, QPen
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QToolTip,
)

from unitdeck.i18n import tr
from unitdeck.model import BusyRole, UnitRole

BUTTONS = (  # action, theme icon, fallback glyph, tooltip (source string)
    ("start", "media-playback-start-symbolic", "▶", "Start"),
    ("stop", "media-playback-stop-symbolic", "■", "Stop"),
    ("restart", "view-refresh-symbolic", "↻", "Restart"),
    ("more", "view-more-symbolic", "⋯", "More actions"),
)
SIZE = 22
GAP = 4


class ActionsDelegate(QStyledItemDelegate):
    triggered = pyqtSignal(str, QModelIndex)  # action, row index in the view's model

    def __init__(self, view: QAbstractItemView) -> None:
        super().__init__(view)
        self._view = view
        self._icons = {action: QIcon.fromTheme(icon) for action, icon, _, _ in BUTTONS}
        self._hover = (-1, -1)  # (row, button)
        self._angle = 0
        self._spinner = QTimer(self)
        self._spinner.setInterval(80)
        self._spinner.timeout.connect(self._spin)
        view.setMouseTracking(True)
        view.viewport().installEventFilter(self)

    def set_spinning(self, on: bool) -> None:
        if on and not self._spinner.isActive():
            self._spinner.start()
        elif not on:
            self._spinner.stop()
            self._view.viewport().update()

    def _spin(self) -> None:
        self._angle = (self._angle - 30) % 360
        self._view.viewport().update()

    # ---- geometry ---------------------------------------------------------------------------

    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex) -> QSize:
        return QSize(len(BUTTONS) * (SIZE + GAP) + GAP, SIZE + 2 * GAP)

    @staticmethod
    def _button_rect(cell: QRect, i: int) -> QRect:
        x = cell.left() + GAP + i * (SIZE + GAP)
        y = cell.top() + (cell.height() - SIZE) // 2
        return QRect(x, y, SIZE, SIZE)

    def _hit(self, cell: QRect, pos) -> int:
        for i in range(len(BUTTONS)):
            if self._button_rect(cell, i).contains(pos):
                return i
        return -1

    # ---- painting ---------------------------------------------------------------------------

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex) -> None:
        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        opt.text = ""
        style = opt.widget.style() if opt.widget else QApplication.style()
        style.drawControl(QStyle.ControlElement.CE_ItemViewItem, opt, painter, opt.widget)

        unit = index.data(UnitRole)
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if index.data(BusyRole):
            rect = self._button_rect(option.rect, 0).adjusted(4, 4, -4, -4)
            painter.setPen(QPen(opt.palette.highlight().color(), 2))
            painter.drawArc(rect, self._angle * 16, 270 * 16)
            painter.restore()
            return
        for i, (action, _icon, glyph, _tip) in enumerate(BUTTONS):
            rect = self._button_rect(option.rect, i)
            enabled = unit.can(action)
            if enabled and self._hover == (index.row(), i):
                color = opt.palette.highlight().color()
                color.setAlpha(70)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(color)
                painter.drawRoundedRect(rect, 4, 4)
            icon = self._icons[action]
            if icon.isNull():
                role = opt.palette.text() if enabled else opt.palette.placeholderText()
                painter.setPen(role.color())
                painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, glyph)
            else:
                mode = QIcon.Mode.Normal if enabled else QIcon.Mode.Disabled
                icon.paint(painter, rect.adjusted(3, 3, -3, -3), Qt.AlignmentFlag.AlignCenter, mode)
        painter.restore()

    # ---- mouse ------------------------------------------------------------------------------

    def editorEvent(self, event, model, option: QStyleOptionViewItem, index: QModelIndex) -> bool:
        if isinstance(event, QMouseEvent):
            pos = event.position().toPoint()
            if event.type() == QEvent.Type.MouseMove:
                hover = (index.row(), self._hit(option.rect, pos))
                if hover != self._hover:
                    self._hover = hover
                    self._view.viewport().update()
            elif (
                event.type() == QEvent.Type.MouseButtonRelease
                and event.button() == Qt.MouseButton.LeftButton
            ):
                i = self._hit(option.rect, pos)
                if i >= 0:
                    action = BUTTONS[i][0]
                    if not index.data(BusyRole) and index.data(UnitRole).can(action):
                        self.triggered.emit(action, index)
                    return True
        return super().editorEvent(event, model, option, index)

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Type.Leave and self._hover != (-1, -1):
            self._hover = (-1, -1)
            self._view.viewport().update()
        return super().eventFilter(obj, event)

    def helpEvent(self, event: QHelpEvent, view, option: QStyleOptionViewItem, index) -> bool:
        if event.type() == QEvent.Type.ToolTip:
            i = self._hit(option.rect, event.pos())
            if i >= 0:
                QToolTip.showText(event.globalPos(), tr(BUTTONS[i][3]), view)
                return True
            QToolTip.hideText()
        return super().helpEvent(event, view, option, index)
