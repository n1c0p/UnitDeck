# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Nicola Palmieri (n1c0p)
import hashlib

from unitdeck.updater import (
    is_dev_version,
    is_newer,
    package_format,
    parse_release,
    parse_sha256,
    restart_command,
    sha256_of,
    version_tuple,
)


def asset(name, url):
    return {"name": name, "browser_download_url": url}


RELEASE = {
    "tag_name": "v0.2.0",
    "html_url": "https://github.com/n1c0p/UnitDeck/releases/tag/v0.2.0",
    "body": "## [0.2.0] - 2026-11-01\n\n### Added\n- Things",
    "assets": [
        asset("unitdeck_0.2.0_amd64.deb.sha256", "https://x/sum"),
        asset("unitdeck_0.2.0_amd64.deb", "https://x/deb"),
        asset("unitdeck-common_0.2.0_amd64.deb", "https://x/common"),
        asset("unitdeck-common_0.2.0_amd64.deb.sha256", "https://x/commonsum"),
        asset("unitdeck-tui_0.2.0_amd64.deb", "https://x/tui"),
        asset("unitdeck-0.2.0-1.x86_64.rpm", "https://x/rpm"),
        asset("unitdeck-0.2.0-1.x86_64.rpm.sha256", "https://x/rpmsum"),
        asset("unitdeck-common-0.2.0-1.x86_64.rpm", "https://x/rpmcommon"),
        asset("unitdeck-tui-0.2.0-1.x86_64.rpm", "https://x/rpmtui"),
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


def test_parse_release_picks_common_and_desktop_packages():
    release = parse_release(RELEASE)
    assert release.version == "0.2.0" and release.notes.startswith("## [0.2.0]")
    assert [(a.name, a.url, a.sha256_url) for a in release.assets] == [
        ("unitdeck-common_0.2.0_amd64.deb", "https://x/common", "https://x/commonsum"),
        ("unitdeck_0.2.0_amd64.deb", "https://x/deb", "https://x/sum"),
    ]
    assert release.deb_name == "unitdeck-common_0.2.0_amd64.deb"  # first download
    rpm = parse_release(RELEASE, ".rpm")
    assert [a.name for a in rpm.assets] == [
        "unitdeck-common-0.2.0-1.x86_64.rpm",
        "unitdeck-0.2.0-1.x86_64.rpm",
    ]
    assert rpm.assets[1].sha256_url == "https://x/rpmsum"
    bare = parse_release({"tag_name": "v0.3.0"})
    assert bare.deb_url == "" and bare.page_url.endswith("/releases")
    assert parse_release(RELEASE, "").deb_url == ""
    single = parse_release(
        {"tag_name": "v0.1.0", "assets": [asset("unitdeck_0.1.0_amd64.deb", "u")]}
    )
    assert single.assets == []  # a release without the common package is not installable


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


def test_restart_command(monkeypatch):
    import sys

    monkeypatch.delattr(sys, "frozen", raising=False)
    assert restart_command() == [sys.executable, "-m", "unitdeck"]
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", "/opt/unitdeck/unitdeck")
    assert restart_command() == ["/opt/unitdeck/unitdeck"]


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
    from unitdeck.updater import Asset

    second = tmp_path / "unitdeck-common_9.9.9_amd64.deb"
    second.write_bytes(b"common")
    updater.download(
        Release(
            "9.9.9",
            "",
            "",
            [Asset(second.name, f"file://{second}"), Asset(source.name, f"file://{source}")],
        )
    )
    loop = QEventLoop()
    QTimer.singleShot(5000, loop.quit)
    poll = QTimer()
    poll.timeout.connect(lambda: loop.quit() if results else None)
    poll.start(20)
    loop.exec()
    QCoreApplication.processEvents()
    assert results == [("ok", f"{target_dir / second.name} {target_dir / source.name}")]
    assert (target_dir / source.name).read_bytes() == b"deb" * 10000
    assert progress and progress[-1][0] == 30000
