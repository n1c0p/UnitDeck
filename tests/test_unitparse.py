# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Nicola Palmieri (n1c0p)
from unitdeck.backend.unitparse import Entry, first_entries, merge, parse, serialize
from unitdeck.templates import load_templates

ORDER = ("Unit", "Service", "Install")
UNIT = """# header comment
[Unit]
Description=Demo
# why we wait
After=network.target
After = other.target

[Service]
ExecStart=/bin/foo \\
    --long-option
ExecStart=
Unknown=kept
garbage line
; semicolon comment

[Install]
WantedBy=multi-user.target
"""


def test_round_trip_is_lossless():
    for text in (UNIT, "", "\n", "[Service]", "[Service]\nA=1\n\n\n", "# only\n"):
        expected = text if text.endswith("\n") or not text else text + "\n"
        assert serialize(parse(text)) == expected
    for template in load_templates():
        assert serialize(parse(template.body)) == template.body


def test_parse_structure():
    unit = parse(UNIT)
    assert unit.preamble == ["# header comment"]
    assert [s.name for s in unit.sections] == ["Unit", "Service", "Install"]
    after = unit.sections[0].entries[1:]
    assert [(e.key, e.value) for e in after] == [
        ("After", "network.target"),
        ("After", "other.target"),
    ]
    assert after[0].lead == ["# why we wait"]
    service = unit.sections[1]
    assert service.entries[0].value == "/bin/foo \\\n    --long-option"
    assert service.entries[1].value == ""  # reset of the list, kept
    assert service.trail == ["garbage line", "; semicolon comment", ""]


def test_changed_value_is_rewritten_untouched_ones_keep_their_spelling():
    unit = parse(UNIT)
    unit.sections[0].entries[2].value = "changed.target"
    out = serialize(unit)
    assert "After=changed.target\n" in out and "After = other" not in out
    assert "ExecStart=/bin/foo \\\n    --long-option\n" in out


def test_merge_replaces_first_section_and_adds_missing_ones_in_order():
    dropin = parse("# drop-in note\n[Service]\nExecStart=\nExecStart=/bin/new\n")
    out = serialize(
        merge(
            dropin,
            {
                "Unit": [Entry("Description", "D")],
                "Service": dropin.sections[0].entries[1:],
                "Install": [Entry("WantedBy", "default.target")],
            },
            ORDER,
        )
    )
    assert out == (
        "# drop-in note\n\n[Unit]\nDescription=D\n\n[Service]\nExecStart=/bin/new\n"
        "\n[Install]\nWantedBy=default.target\n"
    )
    # an empty, missing section is not created; the parsed unit is not modified
    assert serialize(merge(dropin, {"Unit": []}, ORDER)) == serialize(dropin)
    moved = merge(parse(UNIT), {"Unit": list(reversed(parse(UNIT).sections[0].entries))}, ORDER)
    assert serialize(moved).index("other.target") < serialize(moved).index("Description")
    assert serialize(dropin) == "# drop-in note\n[Service]\nExecStart=\nExecStart=/bin/new\n"


def test_first_entries_takes_the_first_section_of_each_name():
    unit = parse("[Service]\nA=1\n[Unit]\nB=2\n[Service]\nC=3\n")
    first = first_entries(unit, ORDER)
    assert [e.key for e in first["Service"]] == ["A"]
    assert [e.key for e in first["Unit"]] == ["B"] and first["Install"] == []
