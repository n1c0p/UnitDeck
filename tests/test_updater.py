# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Nicola Palmieri (n1c0p)
import hashlib

from unitdeck.updater import (
    is_dev_version,
    is_newer,
    package_format,
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
        {"name": "unitdeck-0.2.0-1.x86_64.rpm", "browser_download_url": "https://x/rpm"},
        {"name": "unitdeck-0.2.0-1.x86_64.rpm.sha256", "browser_download_url": "https://x/rpmsum"},
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
    rpm = parse_release(RELEASE, ".rpm")
    assert rpm.deb_name == "unitdeck-0.2.0-1.x86_64.rpm" and rpm.sha256_url == "https://x/rpmsum"
    assert parse_release(RELEASE, "").deb_url == ""


def test_package_format_from_os_release(tmp_path):
    def family(text):
        path = tmp_path / "os-release"
        path.write_text(text)
        return package_format(str(path))

    assert family("ID=ubuntu\nID_LIKE=debian\n") == (".deb", ["pkexec", "apt-get", "install", "-y"])
    assert family('ID="debian"\n')[0] == ".deb"
    assert family("ID=fedora\n")[1][1] == "dnf"
    assert family('ID=nobara\nID_LIKE="fedora"\n')[0] == ".rpm"
    assert family('ID="opensuse-tumbleweed"\nID_LIKE="suse opensuse"\n')[1][1] == "zypper"
    assert family("ID=arch\n") is None
    assert package_format(str(tmp_path / "missing")) is None


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


def test_download_from_a_local_file_url(tmp_path, monkeypatch):
    """The whole download path runs inside Qt's event loop, with no network involved."""
    from PyQt6.QtCore import QCoreApplication, QEventLoop, QStandardPaths, QTimer

    from unitdeck.updater import Release, Updater

    source = tmp_path / "unitdeck_9.9.9_amd64.deb"
    source.write_bytes(b"deb" * 10000)
    target_dir = tmp_path / "downloads"
    target_dir.mkdir()
    monkeypatch.setattr(QStandardPaths, "writableLocation", lambda _kind: str(target_dir))
    updater = Updater()
    results = []
    progress = []
    updater.progress.connect(lambda received, total: progress.append((received, total)))
    updater.downloaded.connect(lambda path: results.append(("ok", path)))
    updater.download_failed.connect(lambda error: results.append(("fail", error)))
    updater.download(Release("9.9.9", "", "", f"file://{source}", source.name))
    loop = QEventLoop()
    QTimer.singleShot(5000, loop.quit)
    poll = QTimer()
    poll.timeout.connect(lambda: loop.quit() if results else None)
    poll.start(20)
    loop.exec()
    QCoreApplication.processEvents()
    assert results == [("ok", str(target_dir / source.name))]
    assert (target_dir / source.name).read_bytes() == b"deb" * 10000
    assert progress and progress[-1][0] == 30000
