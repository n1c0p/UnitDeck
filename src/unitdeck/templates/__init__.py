# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Nicola Palmieri (n1c0p)
"""Service templates: unit files with {PLACEHOLDERS} and a ``# unitdeck:`` header line.

To add a template, drop a ``NN-name.service`` file in this directory with the SPDX header and
a line ``# unitdeck: name=<shown in the wizard>; scope=user|system|both``. Other comment
lines are kept in the generated unit. A line ``Key={PLACEHOLDER}`` is dropped when the value
is empty, so optional directives disappear instead of being written empty.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from importlib.resources import files

PLACEHOLDER = re.compile(r"\{([A-Z][A-Z0-9_]*)\}")
WHOLE_LINE = re.compile(r"^\s*([A-Za-z0-9_.-]+)=\{([A-Z][A-Z0-9_]*)\}\s*$")
# Placeholders the wizard knows how to ask for; anything else becomes a plain text field.
STANDARD = (
    "DESCRIPTION",
    "TYPE",
    "EXEC_START",
    "EXEC_STOP",
    "RESTART",
    "AFTER",
    "WANTS",
    "USER",
    "GROUP",
    "WANTED_BY",
)


@dataclass(slots=True)
class Template:
    id: str
    name: str
    scope: str  # "user", "system" or "both"
    body: str  # without the SPDX and unitdeck header lines

    @property
    def placeholders(self) -> list[str]:
        seen: dict[str, None] = {}
        for match in PLACEHOLDER.finditer(self.body):
            seen.setdefault(match.group(1))
        return list(seen)

    def fits(self, scope: str) -> bool:
        return self.scope in ("both", scope)


def parse_template(template_id: str, text: str) -> Template:
    header: dict[str, str] = {}
    body: list[str] = []
    for line in text.splitlines():
        if line.startswith("# unitdeck:"):
            for item in line[len("# unitdeck:") :].split(";"):
                key, _, value = item.partition("=")
                header[key.strip()] = value.strip()
        elif not line.startswith("# SPDX-"):
            body.append(line)
    if "name" not in header:
        raise ValueError(f"template {template_id}: missing '# unitdeck: name=...' header")
    scope = header.get("scope", "both")
    if scope not in ("user", "system", "both"):
        raise ValueError(f"template {template_id}: scope must be user, system or both")
    return Template(template_id, header["name"], scope, "\n".join(body).strip("\n") + "\n")


def load_templates() -> list[Template]:
    templates = []
    for entry in sorted(files(__package__).iterdir(), key=lambda e: e.name):
        if entry.name.endswith(".service"):
            templates.append(parse_template(entry.name[:-8], entry.read_text(encoding="utf-8")))
    return templates


def render(template: Template, values: dict[str, str]) -> str:
    lines = []
    for line in template.body.splitlines():
        whole = WHOLE_LINE.match(line)
        if whole and not values.get(whole.group(2), "").strip():
            continue  # optional directive left empty
        lines.append(PLACEHOLDER.sub(lambda m: values.get(m.group(1), ""), line))
    return "\n".join(lines).rstrip("\n") + "\n"
