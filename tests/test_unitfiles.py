# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Nicola Palmieri (n1c0p)
import os

import pytest

from unitdeck.backend import unitfiles
from unitdeck.backend.base import Scope


def test_paths_and_ownership(tmp_path):
    own = str(tmp_path / "own")
    assert unitfiles.unit_path("a.service", own) == f"{own}/a.service"
    assert unitfiles.dropin_path("a.service", own) == f"{own}/a.service.d/override.conf"
    assert unitfiles.is_own(f"{own}/a.service", own) and not unitfiles.is_own(
        "/usr/lib/systemd/system/a.service", own
    )
    assert unitfiles.is_own(f"{own}/a.service", own + "/")


def test_vendor_copy(monkeypatch, tmp_path):
    vendor = tmp_path / "vendor"
    vendor.mkdir()
    (vendor / "a.service").write_text("")
    monkeypatch.setitem(
        unitfiles.OTHER_UNIT_DIRS, Scope.USER, (str(tmp_path / "missing"), str(vendor))
    )
    assert unitfiles.vendor_copy("a.service", Scope.USER) == str(vendor / "a.service")
    assert unitfiles.vendor_copy("b.service", Scope.USER) == ""


def test_write_backup_delete(tmp_path):
    own = str(tmp_path)
    unit = unitfiles.unit_path("a.service", own)
    dropin = unitfiles.dropin_path("a.service", own)
    unitfiles.write_file(unit, "v1")
    unitfiles.write_file(unit, "v2")
    unitfiles.write_file(dropin, "d1")
    assert open(unit).read() == "v2" and open(unit + ".bak").read() == "v1"
    assert oct(os.stat(dropin).st_mode & 0o777) == "0o644"
    link = unitfiles.unit_path("m.service", own)
    os.symlink("/dev/null", link)
    with pytest.raises(OSError, match="symlink"):
        unitfiles.write_file(link, "x")
    unitfiles.delete_unit_files(unit, dropin)
    assert sorted(os.listdir(own)) == ["m.service"]


def test_effective_config_and_read_errors(tmp_path):
    frag = tmp_path / "a.service"
    frag.write_text("[Unit]\n")
    parts = unitfiles.effective_config(str(frag), [str(tmp_path / "missing.conf")])
    assert parts[0] == (str(frag), "[Unit]\n")
    assert parts[1][1].startswith("# ")  # unreadable drop-in reported inline, no crash
    assert unitfiles.effective_config("", []) == []


def test_verify_staging_and_filtering():
    staged = unitfiles.stage_for_verify(
        "t.service", "[Service]\nExecStart=/bin/true\n", "[Service]\nNice=1\n"
    )
    try:
        directory = os.path.dirname(staged)
        assert open(staged).read().startswith("[Service]")
        assert (
            open(os.path.join(directory, "t.service.d", "override.conf")).read()
            == "[Service]\nNice=1\n"
        )
        assert unitfiles.verify_args(Scope.USER, staged) == ["verify", "--man=no", "--user", staged]
        assert "--user" not in unitfiles.verify_args(Scope.SYSTEM, staged)
        output = (
            f"{directory}/t.service.d/override.conf:2: Unknown key\n"
            "/usr/lib/systemd/user/other.service:3: noise\n"
            "Unit t.service failed to load\n"
        )
        assert (
            unitfiles.relevant_lines(output, staged)
            == "t.service.d/override.conf:2: Unknown key\nUnit t.service failed to load"
        )
    finally:
        unitfiles.cleanup_staging(staged)
    assert not os.path.exists(os.path.dirname(staged))
