# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Nicola Palmieri (n1c0p)
"""Updates: check GitHub Releases, download the .deb, verify its SHA256, install with pkexec."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path

from PyQt6.QtCore import QFile, QIODevice, QObject, QProcess, QStandardPaths, QUrl, pyqtSignal
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest

from unitdeck import __version__

REPOSITORY = "n1c0p/UnitDeck"
RELEASES_API = f"https://api.github.com/repos/{REPOSITORY}/releases/latest"
RELEASES_PAGE = f"https://github.com/{REPOSITORY}/releases"
INSTALL_COMMAND = ["pkexec", "apt-get", "install", "-y"]  # + absolute path of the .deb


@dataclass(slots=True)
class Release:
    version: str
    notes: str
    page_url: str
    deb_url: str = ""
    deb_name: str = ""
    sha256_url: str = ""


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


def parse_release(data: dict) -> Release:
    release = Release(
        version=data["tag_name"].lstrip("v"),
        notes=data.get("body") or "",
        page_url=data.get("html_url") or RELEASES_PAGE,
    )
    assets = {a["name"]: a["browser_download_url"] for a in data.get("assets", [])}
    for name, url in assets.items():
        if name.endswith(".deb") and "amd64" in name:
            release.deb_name, release.deb_url = name, url
            release.sha256_url = assets.get(name + ".sha256", "")
            break
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
            release = parse_release(json.loads(bytes(reply.readAll())))
        except (ValueError, KeyError, TypeError) as exc:
            self.check_failed.emit(f"unexpected answer from GitHub: {exc}")
            return
        if is_newer(release.version, self.installed):
            self.available.emit(release)
        else:
            self.up_to_date.emit(release.version)

    # ---- download ---------------------------------------------------------------------------

    def download(self, release: Release) -> None:
        folder = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DownloadLocation)
        target = Path(folder) / release.deb_name
        file = QFile(str(target))
        if not file.open(QIODevice.OpenModeFlag.WriteOnly | QIODevice.OpenModeFlag.Truncate):
            self.download_failed.emit(file.errorString())
            return
        reply = self._get(release.deb_url)
        reply.readyRead.connect(lambda: file.write(reply.readAll()))
        reply.downloadProgress.connect(self.progress)
        reply.finished.connect(lambda: self._on_download(reply, file, release, target))

    def _on_download(self, reply: QNetworkReply, file: QFile, release: Release, target: Path):
        file.write(reply.readAll())
        file.close()
        reply.deleteLater()
        if reply.error() != QNetworkReply.NetworkError.NoError:
            target.unlink(missing_ok=True)
            self.download_failed.emit(reply.errorString())
        elif release.sha256_url:
            check = self._get(release.sha256_url)
            check.finished.connect(lambda: self._on_checksum(check, release, target))
        else:
            self.downloaded.emit(str(target))

    def _on_checksum(self, reply: QNetworkReply, release: Release, target: Path) -> None:
        reply.deleteLater()
        if reply.error() != QNetworkReply.NetworkError.NoError:
            target.unlink(missing_ok=True)
            self.download_failed.emit(reply.errorString())
            return
        expected = parse_sha256(bytes(reply.readAll()).decode("utf-8", "replace"), release.deb_name)
        # ponytail: hashing ~150 MB blocks the GUI for well under a second; move to a thread if not
        if expected and expected == sha256_of(target):
            self.downloaded.emit(str(target))
        else:
            target.unlink(missing_ok=True)
            self.download_failed.emit("checksum mismatch")

    # ---- install ----------------------------------------------------------------------------

    def install(self, path: str) -> None:
        """pkexec shows the desktop authentication dialog; apt-get installs the local package."""
        self._proc = QProcess(self)
        self._proc.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self._proc.finished.connect(self._on_installed)
        self._proc.start(INSTALL_COMMAND[0], [*INSTALL_COMMAND[1:], path])

    def _on_installed(self, code: int, _status: object) -> None:
        output = bytes(self._proc.readAllStandardOutput()).decode("utf-8", "replace")
        self._proc.deleteLater()
        self._proc = None
        self.install_finished.emit(code == 0, output)
