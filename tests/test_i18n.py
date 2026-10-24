# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Nicola Palmieri (n1c0p)
import ast
import re
from pathlib import Path

import pytest

from unitdeck import i18n
from unitdeck.gui.actions_delegate import BUTTONS
from unitdeck.gui.unit_tab import ACTION_LABELS, ERROR_LABELS, JOB_RESULTS
from unitdeck.model import COLUMNS, FILTER_LABELS

SRC = Path(i18n.__file__).parent


@pytest.fixture(autouse=True)
def english():
    i18n.set_language("en")
    yield
    i18n.set_language("en")


def source_strings() -> set[str]:
    """Every literal passed to tr(...) plus the label tables translated at use time."""
    found = set()
    for path in SRC.rglob("*.py"):
        if path.name == "i18n.py":
            continue
        for match in re.finditer(
            r"\btr\(\s*('(?:[^'\\]|\\.)*'|\"(?:[^\"\\]|\\.)*\")", path.read_text()
        ):
            found.add(ast.literal_eval(match.group(1)))
    found.update(COLUMNS)
    found.update(FILTER_LABELS.values())
    found.update(ACTION_LABELS.values())
    found.update(JOB_RESULTS.values())
    found.update(ERROR_LABELS.values())
    found.update(button[3] for button in BUTTONS)
    return found


def test_italian_catalogue_is_complete():
    missing = source_strings() - i18n.IT.keys()
    assert not missing, f"add to IT: {sorted(missing)}"


def test_catalogue_has_no_stale_entries():
    stale = i18n.IT.keys() - source_strings()
    assert not stale, f"unused in IT: {sorted(stale)}"


def test_tr_and_language_switch():
    assert i18n.tr("Start") == "Start"
    i18n.set_language("it")
    assert i18n.language() == "it"
    assert i18n.tr("Start") == "Avvia"
    assert i18n.tr("not in catalogue") == "not in catalogue"
    assert i18n.resolve("en") == "en" and i18n.resolve("system") in ("en", "it")
