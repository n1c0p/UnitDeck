# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Nicola Palmieri (n1c0p)
"""Plain text editor with line numbers and syntax highlighting for systemd's INI-like files."""

from __future__ import annotations

import re

from PyQt6.QtCore import QRect, QSize, Qt
from PyQt6.QtGui import (
    QColor,
    QFont,
    QFontDatabase,
    QPainter,
    QSyntaxHighlighter,
    QTextCharFormat,
    QTextDocument,
)
from PyQt6.QtWidgets import QApplication, QPlainTextEdit, QWidget

SECTION = re.compile(r"^\s*\[[^\]]*\]?\s*$")
KEY = re.compile(r"^\s*([A-Za-z0-9_.-]+)\s*(=)(.*)$")
COMMENT = re.compile(r"^\s*[#;]")
LIGHT_COLORS = {"section": "#8250df", "key": "#0969da", "comment": "#6e7781", "path": "#1a7f37"}
DARK_COLORS = {"section": "#c297ff", "key": "#79c0ff", "comment": "#8b949e", "path": "#56d364"}


class IniHighlighter(QSyntaxHighlighter):
    def __init__(self, document: QTextDocument) -> None:
        super().__init__(document)
        dark = QApplication.palette().window().color().lightness() < 128
        colors = DARK_COLORS if dark else LIGHT_COLORS
        self._section = QTextCharFormat()
        self._section.setFontWeight(QFont.Weight.Bold)
        self._section.setForeground(QColor(colors["section"]))
        self._key = QTextCharFormat()
        self._key.setForeground(QColor(colors["key"]))
        self._comment = QTextCharFormat()
        self._comment.setForeground(QColor(colors["comment"]))
        self._comment.setFontItalic(True)
        self._path = QTextCharFormat()
        self._path.setForeground(QColor(colors["path"]))
        self._path.setFontWeight(QFont.Weight.Bold)

    def highlightBlock(self, text: str) -> None:
        if text.startswith("# ") and text[2:].startswith("/"):  # file header in the effective view
            self.setFormat(0, len(text), self._path)
        elif COMMENT.match(text):
            self.setFormat(0, len(text), self._comment)
        elif SECTION.match(text):
            self.setFormat(0, len(text), self._section)
        elif match := KEY.match(text):
            self.setFormat(match.start(1), match.end(1) - match.start(1), self._key)


class CodeEditor(QPlainTextEdit):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont))
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.setTabStopDistance(4 * self.fontMetrics().horizontalAdvance(" "))
        self._gutter = _Gutter(self)
        self.highlighter = IniHighlighter(self.document())
        self.blockCountChanged.connect(self._update_gutter_width)
        self.updateRequest.connect(self._update_gutter)
        self._update_gutter_width()

    def gutter_width(self) -> int:
        digits = max(2, len(str(self.blockCount())))
        return 12 + self.fontMetrics().horizontalAdvance("9") * digits

    def _update_gutter_width(self, *_args: object) -> None:
        self.setViewportMargins(self.gutter_width(), 0, 0, 0)

    def _update_gutter(self, rect: QRect, dy: int) -> None:
        if dy:
            self._gutter.scroll(0, dy)
        else:
            self._gutter.update(0, rect.y(), self._gutter.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self._update_gutter_width()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        area = self.contentsRect()
        self._gutter.setGeometry(QRect(area.left(), area.top(), self.gutter_width(), area.height()))

    def paint_gutter(self, event) -> None:
        painter = QPainter(self._gutter)
        painter.fillRect(event.rect(), self.palette().alternateBase())
        painter.setPen(self.palette().placeholderText().color())
        block = self.firstVisibleBlock()
        top = round(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        width = self._gutter.width() - 6
        height = self.fontMetrics().height()
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and top + height >= event.rect().top():
                number = str(block.blockNumber() + 1)
                painter.drawText(0, top, width, height, Qt.AlignmentFlag.AlignRight, number)
            block = block.next()
            top += round(self.blockBoundingRect(block).height())


class _Gutter(QWidget):
    def __init__(self, editor: CodeEditor) -> None:
        super().__init__(editor)
        self._editor = editor

    def sizeHint(self) -> QSize:
        return QSize(self._editor.gutter_width(), 0)

    def paintEvent(self, event) -> None:
        self._editor.paint_gutter(event)
