# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Nicola Palmieri (n1c0p)
"""Service editor: a form builder ([Unit], [Service], [Install] accordions) and the raw text.

The text is the source of truth. Every form change rewrites it at once; edits made in the
Text tab reach the form when going back to the Builder tab. Comments, unknown directives and
untouched lines survive both ways (see backend.unitparse).
"""

from __future__ import annotations

import html

from PyQt6.QtCore import QMimeData, QPoint, Qt, pyqtSignal
from PyQt6.QtGui import QDrag, QTextCursor, QTextDocument
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QTabWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from unitdeck.backend import directives, unitparse
from unitdeck.backend.directives import SECTIONS, Directive
from unitdeck.backend.unitparse import Entry
from unitdeck.gui.code_editor import CodeEditor
from unitdeck.i18n import tr

ROW_MIME = "application/x-unitdeck-row"
WARNING_STYLE = "color: #bf8700"


def show_info(parent: QWidget, d: Directive) -> None:
    if not d.info:
        text = f"<p>{html.escape(tr('UnitDeck has no description for this directive.'))}</p>"
    else:
        text = (
            f"<p>{html.escape(tr(d.info))}</p>"
            f"<p><b>{html.escape(tr('Example:'))}</b></p>"
            f"<pre>[{d.section}]\n{d.key}={html.escape(d.example)}</pre>"
        )
        if d.choices:
            text += f"<p><b>{html.escape(tr('Values:'))}</b> {', '.join(d.choices)}</p>"
        if d.repeatable:
            text += f"<p>{html.escape(tr('Can be set more than once.'))}</p>"
    text += f"<p><i>man {d.man}</i></p>"
    box = QMessageBox(QMessageBox.Icon.Information, f"{d.key}=", text, parent=parent)
    box.setTextFormat(Qt.TextFormat.RichText)
    box.exec()


class Handle(QLabel):
    """Grip on the left of a row: drag it up or down to reorder the rows of a section."""

    def __init__(self, row: Row) -> None:
        super().__init__("≡")
        self._row = row
        self._press = QPoint()
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.setToolTip(tr("Drag to reorder"))
        font = self.font()
        font.setPointSizeF(font.pointSizeF() * 1.4)
        self.setFont(font)

    def mousePressEvent(self, event) -> None:
        self._press = event.position().toPoint()

    def mouseMoveEvent(self, event) -> None:
        if not event.buttons() & Qt.MouseButton.LeftButton:
            return
        distance = (event.position().toPoint() - self._press).manhattanLength()
        if distance < QApplication.startDragDistance():
            return
        mime = QMimeData()
        mime.setData(ROW_MIME, b"")
        drag = QDrag(self)
        drag.setMimeData(mime)
        drag.setPixmap(self._row.grab())
        drag.setHotSpot(self.mapTo(self._row, self._press))
        self._row.section.dragging = self._row
        drag.exec(Qt.DropAction.MoveAction)
        self._row.section.dragging = None


class Row(QWidget):
    """One directive: drag grip, name, typed editor, info and remove buttons."""

    def __init__(self, section: Accordion, directive: Directive, entry: Entry) -> None:
        super().__init__()
        self.section = section
        self.directive = directive
        self.entry = entry  # keeps lead comments and the original lines
        self._label = QLabel(directive.key)
        self._label.setMinimumWidth(170)
        self._edit = self._make_editor(directive, entry.value)
        info = QToolButton()
        info.setText("ⓘ")
        info.setToolTip(tr("What is this directive for?"))
        info.setAutoRaise(True)
        info.clicked.connect(lambda: show_info(self, directive))
        remove = QToolButton()
        remove.setText("✕")
        remove.setToolTip(tr("Remove this directive"))
        remove.setAutoRaise(True)
        remove.clicked.connect(lambda: section.remove_row(self))
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(Handle(self))
        layout.addWidget(self._label)
        layout.addWidget(self._edit, 1)
        layout.addWidget(info)
        layout.addWidget(remove)
        self._check()

    def _make_editor(self, directive: Directive, value: str) -> QWidget:
        if directive.kind == "enum" and directives.fits_widget(directive, value):
            edit = QComboBox()
            edit.addItems(directive.choices)
            edit.setCurrentText(value)
            edit.currentTextChanged.connect(self._changed)
        elif directive.kind == "bool" and directives.fits_widget(directive, value):
            edit = QCheckBox(tr("enabled"))
            edit.setChecked(bool(directives.parse_bool(value)))
            edit.toggled.connect(self._changed)
        else:  # also a value the typed widget cannot show: plain text, flagged by _check
            edit = QLineEdit(value)
            edit.setPlaceholderText(directive.example)
            if "\n" in value:
                edit.setText(value.replace("\\\n", " ").replace("\n", " "))
                edit.setReadOnly(True)
                edit.setToolTip(tr("Value split over several lines: edit it in the Text tab."))
            edit.textChanged.connect(self._changed)
        return edit

    def value(self) -> str:
        edit = self._edit
        if isinstance(edit, QComboBox):
            return edit.currentText()
        if isinstance(edit, QCheckBox):
            return directives.bool_value(edit.isChecked(), self.entry.orig)
        if edit.isReadOnly():
            return self.entry.value
        return edit.text().strip()

    def to_entry(self) -> Entry:
        e = self.entry
        return Entry(e.key, self.value(), e.lead, e.raw, e.orig)

    def _changed(self) -> None:
        self._check()
        self.section.changed()

    def _check(self) -> None:
        reason = directives.problem(self.directive, self.value())
        self._label.setText(f"⚠ {self.directive.key}" if reason else self.directive.key)
        self._label.setStyleSheet(WARNING_STYLE if reason else "")
        self._label.setToolTip(reason or (tr(self.directive.info) if self.directive.info else ""))


class Accordion(QFrame):
    """Framed, collapsible section: header, its rows, then directive picker + Info + Add."""

    def __init__(self, section: str, on_change) -> None:
        super().__init__()
        self.section = section
        self.changed = on_change
        self.dragging: Row | None = None
        self.rows: list[Row] = []
        self.setObjectName("section")
        self.setStyleSheet("QFrame#section { border: 1px solid palette(mid); border-radius: 6px; }")
        self.setAcceptDrops(True)

        self._header = QToolButton()
        self._header.setText(f"[{section}]")
        self._header.setCheckable(True)
        self._header.setChecked(True)
        self._header.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self._header.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._header.setStyleSheet(
            "QToolButton { border: none; font-weight: bold; padding: 6px;"
            " background: palette(alternate-base); border-top-left-radius: 6px;"
            " border-top-right-radius: 6px; }"
        )
        self._header.toggled.connect(self._toggle)

        self._marker = QFrame()
        self._marker.setFrameShape(QFrame.Shape.HLine)
        self._marker.setStyleSheet("color: palette(highlight);")
        self._marker.setLineWidth(2)
        self._marker.hide()
        self._rows_box = QWidget()
        self._rows_layout = QVBoxLayout(self._rows_box)
        self._rows_layout.setContentsMargins(0, 0, 0, 0)

        self._picker = QComboBox()
        self._info = QPushButton(tr("Info"))
        self._add = QPushButton(tr("Add"))
        self._info.clicked.connect(lambda: show_info(self, self._picker.currentData()))
        self._add.clicked.connect(self._add_picked)
        picker_row = QHBoxLayout()
        picker_row.addWidget(self._picker, 1)
        picker_row.addWidget(self._info)
        picker_row.addWidget(self._add)

        self._body = QWidget()
        body_layout = QVBoxLayout(self._body)
        body_layout.setContentsMargins(8, 4, 8, 8)
        body_layout.addWidget(self._rows_box)
        body_layout.addLayout(picker_row)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(1, 1, 1, 1)
        layout.setSpacing(0)
        layout.addWidget(self._header)
        layout.addWidget(self._body)
        self._toggle(True)
        self._refresh_choices()

    def _toggle(self, open_: bool) -> None:
        self._header.setArrowType(Qt.ArrowType.DownArrow if open_ else Qt.ArrowType.RightArrow)
        self._body.setVisible(open_)

    def _refresh_choices(self) -> None:
        used = {row.directive.key for row in self.rows}
        self._picker.clear()
        for d in directives.CATALOG:
            if d.section == self.section and (d.repeatable or d.key not in used):
                self._picker.addItem(d.key, d)
        self._info.setEnabled(self._picker.count() > 0)
        self._add.setEnabled(self._picker.count() > 0)

    def _add_picked(self) -> None:
        d: Directive = self._picker.currentData()
        self._append(d, Entry(d.key, directives.initial_value(d)))
        self._refresh_choices()
        self.changed()

    def _append(self, directive: Directive, entry: Entry) -> None:
        row = Row(self, directive, entry)
        self.rows.append(row)
        self._rows_layout.addWidget(row)

    def load(self, entries: list[Entry]) -> None:
        for row in self.rows:
            row.setParent(None)
            row.deleteLater()
        self.rows = []
        for e in entries:
            known = directives.lookup(self.section, e.key)
            self._append(known or directives.unknown(self.section, e.key), e)
        self._refresh_choices()

    def entries(self) -> list[Entry]:
        return [row.to_entry() for row in self.rows]

    def remove_row(self, row: Row) -> None:
        self.rows.remove(row)
        row.setParent(None)
        row.deleteLater()
        self._refresh_choices()
        self.changed()

    def move_row(self, row: Row, index: int) -> None:
        self.rows.remove(row)
        self.rows.insert(index, row)
        self._rows_layout.removeWidget(row)
        self._rows_layout.insertWidget(index, row)
        self.changed()

    # ---- drag and drop of rows ----------------------------------------------------------------

    def _drop_index(self, y: float) -> int:
        """Insertion index among the other rows for a drop at ``y`` (rows box coordinates)."""
        others = [r for r in self.rows if r is not self.dragging]
        return sum(1 for r in others if r.geometry().center().y() < y)

    def _accepts(self, event) -> bool:
        return event.mimeData().hasFormat(ROW_MIME) and self.dragging in self.rows

    def dragEnterEvent(self, event) -> None:
        if self._accepts(event):
            event.acceptProposedAction()

    def dragMoveEvent(self, event) -> None:
        if not self._accepts(event):
            return
        event.acceptProposedAction()
        y = self._rows_box.mapFrom(self, event.position().toPoint()).y()
        others = [r for r in self.rows if r is not self.dragging]
        index = self._drop_index(y)
        before = self.rows.index(others[index]) if index < len(others) else len(self.rows)
        self._rows_layout.removeWidget(self._marker)
        self._rows_layout.insertWidget(before, self._marker)
        self._marker.show()

    def dragLeaveEvent(self, _event) -> None:
        self._marker.hide()
        self._rows_layout.removeWidget(self._marker)

    def dropEvent(self, event) -> None:
        if not self._accepts(event):
            return
        self._marker.hide()
        self._rows_layout.removeWidget(self._marker)
        y = self._rows_box.mapFrom(self, event.position().toPoint()).y()
        self.move_row(self.dragging, self._drop_index(y))
        event.acceptProposedAction()


class ServiceEditor(QWidget):
    """Builder and Text tabs over one unit file text. Offers the CodeEditor calls the dialogs
    already use (setPlainText, toPlainText, document) so it drops in where the editor was."""

    changed = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._doc = unitparse.UnitText()
        self._synced = ""  # text the form was last loaded from or rendered to
        self._loading = False
        self._text = CodeEditor()
        self._text.textChanged.connect(self.changed)
        self._preview = CodeEditor()
        self._preview.setReadOnly(True)
        self._sections = {name: Accordion(name, self._form_changed) for name in SECTIONS}

        tools = QWidget()
        tools_layout = QVBoxLayout(tools)
        tools_layout.setSpacing(12)
        for accordion in self._sections.values():
            tools_layout.addWidget(accordion)
        tools_layout.addStretch(1)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(tools)
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.addWidget(QLabel(tr("Preview of the unit file:")))
        right_layout.addWidget(self._preview)
        splitter = QSplitter()
        splitter.addWidget(scroll)
        splitter.addWidget(right)
        splitter.setSizes([600, 450])

        self.tabs = QTabWidget()
        self.tabs.addTab(splitter, tr("Builder"))
        self.tabs.addTab(self._text, tr("Text"))
        self.tabs.currentChanged.connect(self._tab_changed)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.tabs)

    # ---- CodeEditor-like interface ------------------------------------------------------------

    def setPlainText(self, text: str) -> None:
        self._text.setPlainText(text)
        self._load_form()

    def toPlainText(self) -> str:
        return self._text.toPlainText()

    def document(self) -> QTextDocument:
        return self._text.document()

    # ---- sync ---------------------------------------------------------------------------------

    def _load_form(self) -> None:
        """Text -> form."""
        text = self._text.toPlainText()
        self._doc = unitparse.parse(text)
        first = unitparse.first_entries(self._doc, SECTIONS)
        self._loading = True
        for name, accordion in self._sections.items():
            accordion.load(first[name])
        self._loading = False
        self._synced = text
        self._show_preview(text)

    def _form_changed(self) -> None:
        """Form -> text, keeping undo history and the modified flag of the text document."""
        if self._loading:
            return
        entries = {name: a.entries() for name, a in self._sections.items()}
        text = unitparse.serialize(unitparse.merge(self._doc, entries, SECTIONS))
        if text != self._text.toPlainText():
            cursor = QTextCursor(self._text.document())
            cursor.select(QTextCursor.SelectionType.Document)
            cursor.insertText(text)
        self._synced = text
        self._show_preview(text)

    def _show_preview(self, text: str) -> None:
        bar = self._preview.verticalScrollBar()
        position = bar.value()
        self._preview.setPlainText(text)
        bar.setValue(position)

    def _tab_changed(self, index: int) -> None:
        if index == 0 and self._text.toPlainText() != self._synced:
            self._load_form()
