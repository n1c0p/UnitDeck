# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Nicola Palmieri (n1c0p)
from unitdeck.newservice import editor_text, has_exec_start
from unitdeck.templates import load_templates


def test_editor_text_prefills_the_whole_line_placeholders():
    empty = next(t for t in load_templates() if t.id.startswith("10-"))
    text = editor_text(empty, {}, "demo.service", system=True)
    assert "Description=demo\n" in text and "Type=simple\n" in text
    assert "WantedBy=multi-user.target\n" in text and "ExecStart=\n" in text
    assert not has_exec_start(text)
    assert "WantedBy=default.target" in editor_text(empty, {}, "demo", system=False)
    assert has_exec_start(text.replace("ExecStart=\n", "ExecStart=/bin/true\n"))


def test_editor_text_keeps_the_template_fields():
    smb = next(t for t in load_templates() if "gio" in t.id)
    values = {"SERVER": "nas", "SHARE": "data", "CREDENTIALS_FILE": ".smb"}
    text = editor_text(smb, values, "nas.service", system=False)
    assert 'smb://@nas/data" < %h/.smb' in text  # USER is not asked for user services
    assert text.count("ExecStart=") == 1 and has_exec_start(text)
