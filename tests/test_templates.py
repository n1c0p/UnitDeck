# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Nicola Palmieri (n1c0p)
import pytest

from unitdeck.templates import STANDARD, load_templates, parse_template, render


def test_shipped_templates_load_and_are_well_formed():
    templates = load_templates()
    ids = [t.id for t in templates]
    assert ids == sorted(ids) and len(ids) >= 4
    for template in templates:
        assert template.name and template.scope in ("user", "system", "both")
        assert "SPDX" not in template.body and "# unitdeck:" not in template.body
        assert "[Unit]" in template.body and "[Install]" in template.body
    smb = next(t for t in templates if "gio" in t.id)
    assert smb.scope == "user" and not smb.fits("system") and smb.fits("user")
    assert smb.placeholders == ["USER", "SERVER", "SHARE", "CREDENTIALS_FILE"]
    assert all(t.fits("system") for t in templates if t is not smb)


def test_parse_errors():
    with pytest.raises(ValueError, match="missing"):
        parse_template("x", "[Unit]\n")
    with pytest.raises(ValueError, match="scope"):
        parse_template("x", "# unitdeck: name=X; scope=galaxy\n[Unit]\n")


def test_render_drops_empty_optional_lines_and_keeps_comments():
    template = parse_template(
        "t",
        "# SPDX-" + "License-Identifier: GPL-3.0-or-later\n# unitdeck: name=T\n# keep me\n"
        "[Unit]\nDescription={DESCRIPTION}\nAfter={AFTER}\n\n[Service]\nExecStart={EXEC_START}\n"
        "User={USER}\nExecStop=/bin/echo {DESCRIPTION} done\n",
    )
    assert template.placeholders == ["DESCRIPTION", "AFTER", "EXEC_START", "USER"]
    out = render(template, {"DESCRIPTION": "Demo", "EXEC_START": "/bin/true", "USER": " "})
    expected = (
        "# keep me\n[Unit]\nDescription=Demo\n\n[Service]\nExecStart=/bin/true\n"
        "ExecStop=/bin/echo Demo done\n"
    )
    assert out == expected
    assert set(STANDARD) >= {"DESCRIPTION", "EXEC_START", "WANTED_BY"}
