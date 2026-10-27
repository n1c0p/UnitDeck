# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Nicola Palmieri (n1c0p)
"""Unit files on disk: locations, effective configuration, validation staging and writers.

The functions are plain filesystem code. The writers wrap them (user scope: direct writes;
system scope: the privileged helper through pkexec) behind one signal-based interface, using
the backend's runtime for subprocesses, so they work with any toolkit.
"""

from __future__ import annotations

import os
import shutil
import tempfile
from collections.abc import Callable

from unitdeck.backend.base import Scope, Signal, SystemdBackend

DROPIN = "override.conf"
HELPER_PATH = "/usr/libexec/unitdeck/unitdeck-helper"
HELPER_MISSING = "eu.nicop.unitdeck.HelperMissing"
# Where a unit of the same name may come from when the user's copy is removed (own_dir excluded).
OTHER_UNIT_DIRS = {
    Scope.SYSTEM: (
        "/run/systemd/system",
        "/usr/local/lib/systemd/system",
        "/usr/lib/systemd/system",
        "/lib/systemd/system",
    ),
    Scope.USER: (
        "/etc/systemd/user",
        "/run/systemd/user",
        "/usr/local/share/systemd/user",
        "/usr/share/systemd/user",
        "/usr/local/lib/systemd/user",
        "/usr/lib/systemd/user",
    ),
}


def is_own(path: str, own_dir: str) -> bool:
    return path.startswith(own_dir.rstrip("/") + "/")


def vendor_copy(unit_name: str, scope: Scope) -> str:
    """Path of the same unit shipped elsewhere than own_dir, or ''."""
    for directory in OTHER_UNIT_DIRS[scope]:
        path = os.path.join(directory, unit_name)
        if os.path.isfile(path):
            return path
    return ""


def unit_path(unit_name: str, own_dir: str) -> str:
    return os.path.join(own_dir, unit_name)


def dropin_path(unit_name: str, own_dir: str) -> str:
    return os.path.join(own_dir, unit_name + ".d", DROPIN)


def read_text(path: str) -> str:
    try:
        with open(path, encoding="utf-8", errors="replace") as handle:
            return handle.read()
    except OSError as exc:
        return f"# {exc}\n"


def effective_config(fragment_path: str, drop_in_paths: list[str]) -> list[tuple[str, str]]:
    """(path, content) of the fragment and every drop-in, like ``systemctl cat``."""
    return [(path, read_text(path)) for path in [fragment_path, *drop_in_paths] if path]


# ---- validation -----------------------------------------------------------------------------


def stage_for_verify(unit_name: str, unit_text: str, dropin_text: str | None = None) -> str:
    """Write the unit (and optionally a drop-in) in a fresh temporary directory.

    Returns the staged unit path; the caller removes the directory with cleanup_staging().
    """
    directory = tempfile.mkdtemp(prefix="unitdeck-verify-")
    path = os.path.join(directory, unit_name)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(unit_text)
    if dropin_text is not None:
        os.mkdir(path + ".d")
        with open(os.path.join(path + ".d", DROPIN), "w", encoding="utf-8") as handle:
            handle.write(dropin_text)
    return path


def verify_args(scope: Scope, staged_unit: str) -> list[str]:
    args = ["verify", "--man=no"]
    if scope is Scope.USER:
        args.append("--user")
    return [*args, staged_unit]


def relevant_lines(output: str, staged_unit: str) -> str:
    """Keep what concerns the staged unit; verify also complains about unrelated installed units."""
    directory = os.path.dirname(staged_unit) + "/"
    name = os.path.basename(staged_unit)
    kept = [
        line.replace(directory, "")
        for line in output.splitlines()
        if directory in line or name in line
    ]
    return "\n".join(kept)


def cleanup_staging(staged_unit: str) -> None:
    shutil.rmtree(os.path.dirname(staged_unit), ignore_errors=True)


# ---- writing (user scope; the helper does the same under /etc) ------------------------------


def write_file(path: str, content: str) -> None:
    """Backup the previous file as .bak, then replace atomically. Symlinks are never overwritten."""
    if os.path.islink(path):
        raise OSError(f"{path} is a symlink (mask or alias), refusing to overwrite it")
    directory = os.path.dirname(path)
    os.makedirs(directory, mode=0o755, exist_ok=True)
    if os.path.exists(path):
        shutil.copy2(path, path + ".bak")
    fd, tmp = tempfile.mkstemp(prefix=".unitdeck-", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
        os.chmod(tmp, 0o644)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def remove_dropin_files(path: str) -> None:
    for candidate in (path, path + ".bak"):
        if os.path.islink(candidate) or os.path.isfile(candidate):
            os.unlink(candidate)
    directory = os.path.dirname(path)
    if os.path.isdir(directory) and not os.listdir(directory):
        os.rmdir(directory)


def delete_unit_files(path: str, dropin: str) -> None:
    if os.path.islink(path):
        raise OSError(f"{path} is a symlink (mask or alias): unmask or disable it instead")
    if not os.path.isfile(path):
        raise OSError(f"{path} does not exist")
    os.unlink(path)
    if os.path.isfile(path + ".bak"):
        os.unlink(path + ".bak")
    remove_dropin_files(dropin)


# ---- writers --------------------------------------------------------------------------------


class UnitWriter:
    """Writes unit files for one scope and reloads the manager afterwards."""

    def __init__(self, backend: SystemdBackend) -> None:
        self._backend = backend
        self.finished = Signal()  # (operation "save" / "delete", ok, detail)

    def write_dropin(self, unit_name: str, content: str) -> None:
        raise NotImplementedError

    def write_unit(self, unit_name: str, content: str) -> None:
        raise NotImplementedError

    def delete_unit(self, unit_name: str) -> None:
        raise NotImplementedError


class UserWriter(UnitWriter):
    def __init__(self, backend: SystemdBackend) -> None:
        super().__init__(backend)
        self._own = backend.own_dir

    def write_dropin(self, unit_name: str, content: str) -> None:
        self._do("save", lambda: write_file(dropin_path(unit_name, self._own), content))

    def write_unit(self, unit_name: str, content: str) -> None:
        self._do("save", lambda: write_file(unit_path(unit_name, self._own), content))

    def delete_unit(self, unit_name: str) -> None:
        self._do(
            "delete",
            lambda: delete_unit_files(
                unit_path(unit_name, self._own), dropin_path(unit_name, self._own)
            ),
        )

    def _do(self, operation: str, action: Callable[[], None]) -> None:
        try:
            action()
        except OSError as exc:
            self.finished.emit(operation, False, str(exc))
            return
        self._backend.daemon_reload()
        self.finished.emit(operation, True, "")


class HelperWriter(UnitWriter):
    """pkexec + unitdeck-helper: polkit asks for the password, the helper writes under /etc."""

    def write_dropin(self, unit_name: str, content: str) -> None:
        self._run("save", ["write-dropin", unit_name], content)

    def write_unit(self, unit_name: str, content: str) -> None:
        self._run("save", ["write-unit", unit_name], content)

    def delete_unit(self, unit_name: str) -> None:
        self._run("delete", ["delete-unit", unit_name])

    def _run(self, operation: str, args: list[str], content: str | None = None) -> None:
        if not os.path.isfile(HELPER_PATH):
            self.finished.emit(operation, False, f"{HELPER_MISSING}: {HELPER_PATH}")
            return
        self._backend.runtime.run(
            ["pkexec", HELPER_PATH, *args, "--reload"],
            content if content is not None else "",
            lambda code, _out, err: self._done(operation, code, err.strip()),
        )

    def _done(self, operation: str, code: int, stderr: str) -> None:
        if code == 0:
            self.finished.emit(operation, True, "")
        elif code in (126, 127):  # pkexec: dialog dismissed / not authorized
            self.finished.emit(
                operation, False, f"org.freedesktop.DBus.Error.AccessDenied: {stderr or 'pkexec'}"
            )
        else:
            self.finished.emit(operation, False, stderr or f"helper exited with status {code}")
