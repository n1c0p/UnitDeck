# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Nicola Palmieri (n1c0p)
"""The privileged helper: unit name validation, path confinement, write/delete semantics."""

import importlib.util
import os
from pathlib import Path

import pytest

HELPER = Path(__file__).resolve().parent.parent / "helper" / "unitdeck-helper"
spec = importlib.util.spec_from_loader(
    "unitdeck_helper", importlib.machinery.SourceFileLoader("unitdeck_helper", str(HELPER))
)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


@pytest.fixture
def root(tmp_path):
    etc = tmp_path / "etc" / "systemd" / "system"
    etc.mkdir(parents=True)
    return etc


@pytest.mark.parametrize(
    "name",
    [
        "../evil.service",
        "a/b.service",
        "x.service/../y.service",
        ".hidden.service",
        "a..b.service",
        "evil.timer",
        "no-suffix",
        "",
        "a\0b.service",
        "x" * 300 + ".service",
    ],
)
def test_rejects_bad_unit_names(name):
    with pytest.raises(helper.HelperError):
        helper.check_unit_name(name)


@pytest.mark.parametrize(
    "name", ["foo.service", "my-app_1.service", "tmpl@inst.service", "tmpl@.service", "a:b.service"]
)
def test_accepts_valid_unit_names(name):
    assert helper.check_unit_name(name) == name


def test_write_dropin_and_unit_with_backup(root):
    message = helper.run(
        ["write-dropin", "foo.service"], root=str(root), content="[Service]\nNice=5\n"
    )
    dropin = root / "foo.service.d" / "override.conf"
    assert "written" in message and dropin.read_text() == "[Service]\nNice=5\n"
    assert oct(dropin.stat().st_mode & 0o777) == "0o644"
    helper.run(["write-dropin", "foo.service"], root=str(root), content="[Service]\nNice=7\n")
    assert (root / "foo.service.d" / "override.conf.bak").read_text() == "[Service]\nNice=5\n"
    helper.run(
        ["write-unit", "bar.service"], root=str(root), content="[Service]\nExecStart=/bin/true\n"
    )
    assert (root / "bar.service").read_text().startswith("[Service]")


def test_refuses_symlinks_and_escapes(root, tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    (root / "alias.service").symlink_to("/dev/null")
    with pytest.raises(helper.HelperError, match="symlink"):
        helper.run(["write-unit", "alias.service"], root=str(root), content="x")
    with pytest.raises(helper.HelperError, match="symlink"):
        helper.run(["delete-unit", "alias.service"], root=str(root))
    (root / "esc.service.d").symlink_to(outside)
    with pytest.raises(helper.HelperError, match="outside"):
        helper.run(["write-dropin", "esc.service"], root=str(root), content="x")
    assert not list(outside.iterdir())


def test_remove_dropin_and_delete_unit(root):
    helper.run(["write-unit", "foo.service"], root=str(root), content="a")
    helper.run(["write-unit", "foo.service"], root=str(root), content="b")
    helper.run(["write-dropin", "foo.service"], root=str(root), content="c")
    assert helper.run(["remove-dropin", "foo.service"], root=str(root)).startswith("removed")
    assert not (root / "foo.service.d").exists()
    assert helper.run(["remove-dropin", "foo.service"], root=str(root)) == "nothing to remove"
    helper.run(["write-dropin", "foo.service"], root=str(root), content="c")
    helper.run(["delete-unit", "foo.service"], root=str(root))
    assert sorted(os.listdir(root)) == []
    with pytest.raises(helper.HelperError, match="does not exist"):
        helper.run(["delete-unit", "foo.service"], root=str(root))


def test_usage_errors(root):
    for argv in (
        [],
        ["explode"],
        ["write-unit"],
        ["write-unit", "a.service", "b.service"],
        ["daemon-reload", "x"],
    ):
        with pytest.raises(helper.UsageError):
            helper.run(argv, root=str(root), content="")
