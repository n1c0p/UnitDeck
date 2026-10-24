# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Nicola (n1c0p)
import hashlib

from unitdeck.updater import (
    is_dev_version,
    is_newer,
    parse_release,
    parse_sha256,
    sha256_of,
    version_tuple,
)

RELEASE = {
    "tag_name": "v0.2.0",
    "html_url": "https://github.com/n1c0p/UnitDeck/releases/tag/v0.2.0",
    "body": "## [0.2.0] - 2026-11-01\n\n### Added\n- Things",
    "assets": [
        {"name": "unitdeck_0.2.0_amd64.deb.sha256", "browser_download_url": "https://x/sum"},
        {"name": "unitdeck_0.2.0_amd64.deb", "browser_download_url": "https://x/deb"},
    ],
}


def test_version_parsing_and_comparison():
    assert version_tuple("v1.2.3") == (1, 2, 3, 0)
    assert version_tuple("0.1.dev6+g1234") == (0, 1, 0, -1)
    assert version_tuple("garbage") == ()
    assert is_newer("0.2.0", "0.1.9") and not is_newer("0.2.0", "0.2.0")
    assert is_newer("0.1.0", "0.1.dev6+g1234")
    assert is_dev_version("0.1.dev6+g1234") and is_dev_version("0.0.0+unknown")
    assert not is_dev_version("0.1.0")


def test_parse_release_picks_deb_and_checksum():
    release = parse_release(RELEASE)
    assert release.version == "0.2.0"
    assert release.deb_name == "unitdeck_0.2.0_amd64.deb"
    assert release.deb_url == "https://x/deb" and release.sha256_url == "https://x/sum"
    assert release.notes.startswith("## [0.2.0]")
    bare = parse_release({"tag_name": "v0.3.0"})
    assert bare.deb_url == "" and bare.page_url.endswith("/releases")


def test_parse_sha256_formats():
    digest = "a" * 64
    assert parse_sha256(digest, "x.deb") == digest
    assert parse_sha256(f"{digest}  x.deb\n", "x.deb") == digest
    assert parse_sha256(f"{'b' * 64} *other.deb\n{digest} *x.deb\n", "x.deb") == digest
    assert parse_sha256("not a checksum", "x.deb") == ""


def test_sha256_of(tmp_path):
    path = tmp_path / "f.bin"
    path.write_bytes(b"unitdeck" * 1000)
    assert sha256_of(path) == hashlib.sha256(b"unitdeck" * 1000).hexdigest()
