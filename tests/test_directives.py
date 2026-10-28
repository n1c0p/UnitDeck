# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Nicola Palmieri (n1c0p)
import pytest

from unitdeck import i18n
from unitdeck.backend.directives import (
    CATALOG,
    SECTIONS,
    fits_widget,
    lookup,
    parse_bool,
    problem,
    unknown,
)


@pytest.fixture(autouse=True)
def english():
    i18n.set_language("en")


def test_catalogue_is_well_formed():
    keys = [(d.section, d.key) for d in CATALOG]
    assert len(keys) == len(set(keys))
    for d in CATALOG:
        assert d.section in SECTIONS and d.info and d.man
        assert d.kind in ("text", "enum", "bool", "time", "path", "paths", "user", "group")
        assert (d.kind == "enum") == bool(d.choices)
        assert problem(d, d.example) == "" or d.kind in ("user", "group"), d.key


def test_checks():
    def check(key, value, section="Service"):
        return problem(lookup(section, key), value)

    assert check("Restart", "on-failure") == "" and "one of" in check("Restart", "sometimes")
    assert check("ProtectSystem", "true") == ""  # booleans are accepted where yes/no are
    assert check("PrivateTmp", "on") == "" and check("PrivateTmp", "maybe") == "Expected yes or no."
    for ok in ("5s", "1min 30s", "infinity", "100ms", "2h", "0"):
        assert check("RestartSec", ok) == "", ok
    assert "time span" in check("RestartSec", "five seconds")
    assert check("WorkingDirectory", "~") == "" and check("EnvironmentFile", "-/etc/x") == ""
    assert "absolute" in check("WorkingDirectory", "relative/dir")
    assert check("ReadWritePaths", "/a -/b") == "" and "absolute" in check("ReadWritePaths", "/a b")
    assert check("User", "root") == "" and check("User", "0") == "" and check("User", "%i") == ""
    assert "No user" in check("User", "no-such-user-unitdeck")
    assert check("ExecStart", "") == "" and check("RestartSec", "") == ""  # empty resets


def test_unknown_directives_are_flagged_with_a_suggestion():
    assert problem(unknown("Service", "Restrat"), "always").endswith("Did you mean Restart?")
    assert problem(unknown("Service", "LimitCORE"), "0") == "Not in UnitDeck's catalogue."


def test_widgets_and_booleans():
    assert parse_bool("On") is True and parse_bool("0") is False and parse_bool("x") is None
    assert fits_widget(lookup("Service", "Type"), "simple")
    assert not fits_widget(lookup("Service", "Type"), "weird")
    assert not fits_widget(lookup("Service", "PrivateTmp"), "disconnected")
    assert not fits_widget(lookup("Service", "ExecStart"), "/bin/a \\\n --b")
