# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Nicola Palmieri (n1c0p)
"""Updates: check GitHub Releases, download the .deb, verify its SHA256, install with pkexec."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

from PyQt6.QtCore import QFile, QIODevice, QObject, QProcess, QStandardPaths, QUrl, pyqtSignal
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest

from unitdeck import __version__

REPOSITORY = "n1c0p/UnitDeck"
RELEASES_API = f"https://api.github.com/repos/{REPOSITORY}/releases/latest"
RELEASES_PAGE = f"https://github.com/{REPOSITORY}/releases"
# Package format and installer per distribution family (ID / ID_LIKE of /etc/os-release).
PACKAGE_FAMILIES = (
    ({"debian", "ubuntu"}, ".deb", ["pkexec", "apt-get", "install", "-y"]),
    ({"fedora", "rhel", "centos"}, ".rpm", ["pkexec", "dnf", "install", "-y"]),
    (
        {"suse", "opensuse"},
        ".rpm",
        ["pkexec", "zypper", "--non-interactive", "install", "--allow-unsigned-rpm"],
    ),
)
ARCHITECTURES = ("amd64", "x86_64")


@dataclass(slots=True)
class Asset:
    name: str
    url: str
    sha256_url: str = ""


@dataclass(slots=True)
class Release:
    version: str
    notes: str
    page_url: str
    assets: list[Asset] = field(default_factory=list)  # packages to download, in order

    @property
    def deb_url(self) -> str:  # "" when the release has no package for this system
        return self.assets[0].url if self.assets else ""

    @property
    def deb_name(self) -> str:
        return self.assets[0].name if self.assets else ""


# Packages the desktop application updates: its own plus the shared helper package.
PACKAGES = ("unitdeck-common", "unitdeck")


def restart_command() -> list[str]:
    """argv that starts a fresh instance: the packaged binary, or python -m unitdeck from source."""
    if getattr(sys, "frozen", False):
        return [sys.executable]
    return [sys.executable, "-m", "unitdeck"]


def version_tuple(text: str) -> tuple[int, ...]:
    """'v1.2.3' -> (1, 2, 3, 0). A dev build sorts below its release: '0.1.dev6' -> (0, 1, 0, -1).

    Returns () when unparsable.
    """
    match = re.match(r"v?(\d+)\.(\d+)(?:\.(\d+))?", text)
    if not match:
        return ()
    return (*(int(part or 0) for part in match.groups()), -1 if "dev" in text else 0)


def is_dev_version(text: str) -> bool:
    return "dev" in text or "unknown" in text


def is_newer(candidate: str, installed: str) -> bool:
    return version_tuple(candidate) > version_tuple(installed)


def package_format(os_release: str = "/etc/os-release") -> tuple[str, list[str]] | None:
    """(package suffix, install command) for this distribution, None when unsupported."""
    ids: set[str] = set()
    try:
        for line in Path(os_release).read_text(encoding="utf-8").splitlines():
            key, _, value = line.partition("=")
            if key.strip() in ("ID", "ID_LIKE"):
                ids.update(value.strip().strip('"').split())
    except OSError:
        return None
    for family, suffix, command in PACKAGE_FAMILIES:
        if ids & family:
            return suffix, command
    return None


def parse_release(data: dict, suffix: str = ".deb") -> Release:
    """Release metadata with the package asset for ``suffix`` (``""`` selects none)."""
    release = Release(
        version=data["tag_name"].lstrip("v"),
        notes=data.get("body") or "",
        page_url=data.get("html_url") or RELEASES_PAGE,
    )
    assets = {a["name"]: a["browser_download_url"] for a in data.get("assets", [])}
    for package in PACKAGES:
        # unitdeck-common_1.2.3_amd64.deb / unitdeck-common-1.2.3-1.x86_64.rpm
        pattern = re.compile(
            rf"^{re.escape(package)}[_-]\d.*({'|'.join(ARCHITECTURES)}).*{re.escape(suffix)}$"
        )
        for name, url in assets.items():
            if suffix and pattern.match(name):
                release.assets.append(Asset(name, url, assets.get(name + ".sha256", "")))
                break
    if len(release.assets) != len(PACKAGES):  # older releases shipped one package: skip them
        release.assets = []
    return release


def parse_sha256(text: str, filename: str) -> str:
    """Accept 'HASH', 'HASH  file' or 'HASH *file' lines; the one naming ``filename`` wins."""
    fallback = ""
    for line in text.splitlines():
        parts = line.split()
        if not parts or len(parts[0]) != 64:
            continue
        if len(parts) == 1 or parts[-1].lstrip("*") == filename:
            return parts[0].lower()
        fallback = fallback or parts[0].lower()
    return fallback


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1 << 20):
            digest.update(chunk)
    return digest.hexdigest()


class Updater(QObject):
    available = pyqtSignal(object)  # Release
    up_to_date = pyqtSignal(str)  # latest version
    check_failed = pyqtSignal(str)
    progress = pyqtSignal(int, int)  # received, total bytes
    downloaded = pyqtSignal(str)  # verified file path
    download_failed = pyqtSignal(str)
    install_finished = pyqtSignal(bool, str)  # ok, output

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.installed = __version__
        self.format = package_format()  # None on distributions without a package
        self._nam = QNetworkAccessManager(self)
        self._proc: QProcess | None = None

    def _get(self, url: str) -> QNetworkReply:
        request = QNetworkRequest(QUrl(url))
        request.setHeader(QNetworkRequest.KnownHeaders.UserAgentHeader, f"UnitDeck/{__version__}")
        request.setRawHeader(b"Accept", b"application/vnd.github+json")
        request.setAttribute(
            QNetworkRequest.Attribute.RedirectPolicyAttribute,
            QNetworkRequest.RedirectPolicy.NoLessSafeRedirectPolicy,
        )
        return self._nam.get(request)

    # ---- check ------------------------------------------------------------------------------

    def check(self) -> None:
        reply = self._get(RELEASES_API)
        reply.finished.connect(lambda: self._on_check(reply))

    def _on_check(self, reply: QNetworkReply) -> None:
        reply.deleteLater()
        if reply.error() != QNetworkReply.NetworkError.NoError:
            self.check_failed.emit(reply.errorString())
            return
        try:
            suffix = self.format[0] if self.format else ""
            release = parse_release(json.loads(bytes(reply.readAll())), suffix)
        except (ValueError, KeyError, TypeError) as exc:
            self.check_failed.emit(f"unexpected answer from GitHub: {exc}")
            return
        if is_newer(release.version, self.installed):
            self.available.emit(release)
        else:
            self.up_to_date.emit(release.version)

    # ---- download ---------------------------------------------------------------------------

    def download(self, release: Release) -> None:
        """Download every asset of the release in turn; ``downloaded`` carries the paths."""
        self._download_next(release, list(release.assets), [])

    def _download_next(self, release: Release, pending: list[Asset], done: list[Path]) -> None:
        if not pending:
            self.downloaded.emit(" ".join(str(path) for path in done))
            return
        asset = pending[0]
        folder = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DownloadLocation)
        target = Path(folder) / asset.name
        file = QFile(str(target))
        if not file.open(QIODevice.OpenModeFlag.WriteOnly | QIODevice.OpenModeFlag.Truncate):
            self.download_failed.emit(file.errorString())
            return
        reply = self._get(asset.url)
        reply.readyRead.connect(lambda: file.write(reply.readAll()))
        # downloadProgress carries qint64 values: relay them, a direct signal-to-signal
        # connection to an (int, int) signal is refused by Qt.
        reply.downloadProgress.connect(lambda received, total: self.progress.emit(received, total))
        reply.finished.connect(
            lambda: self._on_download(reply, file, asset, target, release, pending, done)
        )

    def _on_download(self, reply, file, asset: Asset, target: Path, release, pending, done):
        file.write(reply.readAll())
        file.close()
        reply.deleteLater()
        if reply.error() != QNetworkReply.NetworkError.NoError:
            target.unlink(missing_ok=True)
            self.download_failed.emit(reply.errorString())
            return

        def verified() -> None:
            self._download_next(release, pending[1:], [*done, target])

        if asset.sha256_url:
            check = self._get(asset.sha256_url)
            check.finished.connect(lambda: self._on_checksum(check, asset, target, verified))
        else:
            verified()

    def _on_checksum(self, reply, asset: Asset, target: Path, then) -> None:
        reply.deleteLater()
        if reply.error() != QNetworkReply.NetworkError.NoError:
            target.unlink(missing_ok=True)
            self.download_failed.emit(reply.errorString())
            return
        expected = parse_sha256(bytes(reply.readAll()).decode("utf-8", "replace"), asset.name)
        # ponytail: hashing ~150 MB blocks the GUI for well under a second; move to a thread if not
        if expected and expected == sha256_of(target):
            then()
        else:
            target.unlink(missing_ok=True)
            self.download_failed.emit("checksum mismatch")

    # ---- install ----------------------------------------------------------------------------

    def install(self, paths: str) -> None:
        """pkexec shows the desktop authentication dialog; the package manager installs the files
        (space-separated absolute paths, as ``downloaded`` gives them)."""
        if self.format is None:
            self.install_finished.emit(False, "no package manager known for this system")
            return
        command = self.format[1]
        self._proc = QProcess(self)
        self._proc.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self._proc.finished.connect(self._on_installed)
        self._proc.start(command[0], [*command[1:], *paths.split(" ")])

    def _on_installed(self, code: int, _status: object) -> None:
        output = bytes(self._proc.readAllStandardOutput()).decode("utf-8", "replace")
        self._proc.deleteLater()
        self._proc = None
        self.install_finished.emit(code == 0, output)
