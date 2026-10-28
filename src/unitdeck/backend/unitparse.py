# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Nicola Palmieri (n1c0p)
"""Lossless parse and serialize of systemd's INI-like unit files, for the form editor.

Comments, blank lines and lines that are not ``Key=value`` stay attached to the directive that
follows them (``lead``) or to the end of their section (``trail``), so a text -> form -> text
round trip gives back the same file. A directive whose value was not changed is written back
from its original lines, keeping spacing and ``\\`` line continuations.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, replace

KEY_LINE = re.compile(r"^\s*[A-Za-z0-9_.-]+\s*=")


@dataclass(slots=True)
class Entry:
    key: str
    value: str
    lead: list[str] = field(default_factory=list)  # comments and blank lines before it
    raw: list[str] = field(default_factory=list)  # original lines, reused while value == orig
    orig: str | None = None

    def lines(self) -> list[str]:
        own = self.raw if self.raw and self.value == self.orig else [f"{self.key}={self.value}"]
        return self.lead + own


@dataclass(slots=True)
class Section:
    name: str
    header: str
    entries: list[Entry] = field(default_factory=list)
    trail: list[str] = field(default_factory=list)  # comments and blank lines after the last entry


@dataclass(slots=True)
class UnitText:
    preamble: list[str] = field(default_factory=list)
    sections: list[Section] = field(default_factory=list)


def parse(text: str) -> UnitText:
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()  # the final newline
    unit = UnitText()
    pending: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            if unit.sections:
                unit.sections[-1].trail = pending
            else:
                unit.preamble = pending
            pending = []
            unit.sections.append(Section(stripped[1:-1].strip(), line))
        elif unit.sections and KEY_LINE.match(line):
            raw = [line]
            while raw[-1].rstrip().endswith("\\") and i + 1 < len(lines):
                i += 1
                raw.append(lines[i])
            key, _, value = "\n".join(raw).partition("=")
            value = value.strip()
            unit.sections[-1].entries.append(Entry(key.strip(), value, pending, raw, value))
            pending = []
        else:
            pending.append(line)  # comment, blank, or something systemd will complain about
        i += 1
    if unit.sections:
        unit.sections[-1].trail = pending
    else:
        unit.preamble = pending
    return unit


def serialize(unit: UnitText) -> str:
    lines = list(unit.preamble)
    for section in unit.sections:
        lines.append(section.header)
        for entry in section.entries:
            lines.extend(entry.lines())
        lines.extend(section.trail)
    return "\n".join(lines) + "\n" if lines else ""


def merge(unit: UnitText, entries: dict[str, list[Entry]], order: tuple[str, ...]) -> UnitText:
    """``unit`` with the entries of the first section of each name in ``entries`` replaced.

    A name in ``entries`` with no section in ``unit`` gets a new one when it has entries,
    placed before the first section that comes later in ``order``, or at the end.
    """
    sections = list(unit.sections)
    done = set()
    for index, section in enumerate(sections):
        if section.name in entries and section.name not in done:
            sections[index] = replace(section, entries=entries[section.name])
            done.add(section.name)
    for name in order:
        if name in done or not entries.get(name):
            continue
        later = set(order[order.index(name) + 1 :])
        at = next((i for i, s in enumerate(sections) if s.name in later), len(sections))
        new = Section(name, f"[{name}]", entries[name], [""] if at < len(sections) else [])
        if at:
            before = sections[at - 1]
            last = (before.entries[-1].lines()[-1:] if before.entries else []) + before.trail
            if (last or [before.header])[-1].strip():
                sections[at - 1] = replace(before, trail=before.trail + [""])
        elif unit.preamble and unit.preamble[-1].strip():
            unit = replace(unit, preamble=unit.preamble + [""])
        sections.insert(at, new)
        done.add(name)
    return replace(unit, sections=sections)
