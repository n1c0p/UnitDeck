# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Nicola Palmieri (n1c0p)
"""Backend on org.freedesktop.systemd1, shared by the system and user buses and by every toolkit."""

from __future__ import annotations

import os

from unitdeck.backend.base import Runtime, Scope, SystemdBackend, Transport, Unit
from unitdeck.backend.unitfiles import HelperWriter, UserWriter, is_own, vendor_copy

MANAGER_PATH = "/org/freedesktop/systemd1"
MANAGER_IFACE = "org.freedesktop.systemd1.Manager"
UNIT_IFACE = "org.freedesktop.systemd1.Unit"
SERVICE_IFACE = "org.freedesktop.systemd1.Service"
PROPERTIES_IFACE = "org.freedesktop.DBus.Properties"

JOB_METHODS = {
    "start": "StartUnit",
    "stop": "StopUnit",
    "restart": "RestartUnit",
    "reload": "ReloadUnit",
}
FILE_METHODS = {  # action -> (method, signature, arguments after the unit name list)
    "enable": ("EnableUnitFiles", "asbb", [False, False]),  # runtime, force
    "disable": ("DisableUnitFiles", "asb", [False]),
    "mask": ("MaskUnitFiles", "asbb", [False, False]),
    "unmask": ("UnmaskUnitFiles", "asb", [False]),
    "revert": (
        "RevertUnitFiles",
        "as",
        [],
    ),  # drops drop-ins and /etc copies, like systemctl revert
}
SIMPLE_METHODS = {"reset-failed": "ResetFailedUnit"}  # no job, no reload
PROPERTY_FIELDS = {
    "ActiveState": "active_state",
    "SubState": "sub_state",
    "LoadState": "load_state",
    "UnitFileState": "unit_file_state",
    "Description": "description",
    "FragmentPath": "fragment_path",
}
REFRESH_DEBOUNCE_MS = 300


def template_of(name: str) -> str:
    """'foo@bar.service' -> 'foo@.service'; '' when the name is not an instance."""
    prefix, at, rest = name.partition("@")
    return f"{prefix}@.{rest.rpartition('.')[2]}" if at else ""


class DBusBackend(SystemdBackend):
    def __init__(self, scope: Scope, transport: Transport, runtime: Runtime) -> None:
        super().__init__(scope, runtime)
        self._t = transport
        self._path_to_name: dict[str, str] = {}
        self._jobs: dict[str, tuple[str, str]] = {}  # job object path -> (unit, action)
        self._early_results: dict[str, str] = {}  # JobRemoved seen before the method reply
        self._lists: dict[str, list] = {}  # ListUnits / ListUnitFiles replies of one refresh
        self._refresh_pending = False

        # Without Subscribe the manager emits no UnitNew/UnitRemoved/JobRemoved/PropertiesChanged.
        self._t.call(MANAGER_PATH, MANAGER_IFACE, "Subscribe", [], _ignore, _ignore)
        for signal in ("UnitNew", "UnitRemoved", "UnitFilesChanged"):
            self._t.subscribe(MANAGER_PATH, MANAGER_IFACE, signal, self._schedule_refresh)
        self._t.subscribe(MANAGER_PATH, MANAGER_IFACE, "Reloading", self._on_reloading)
        self._t.subscribe(MANAGER_PATH, MANAGER_IFACE, "JobRemoved", self._on_job_removed)
        self._t.subscribe("", PROPERTIES_IFACE, "PropertiesChanged", self._on_properties_changed)

    # ---- public API -------------------------------------------------------------------------

    def refresh(self) -> None:
        self._lists = {}
        for member in ("ListUnits", "ListUnitFiles"):
            self._t.call(
                MANAGER_PATH,
                MANAGER_IFACE,
                member,
                [],
                lambda args, member=member: self._on_list(member, args[0]),
                self._error_handler("", "refresh"),
            )

    def fetch_details(self, name: str) -> None:
        unit = self.units.get(name)
        if unit is None:
            return
        if unit.loaded:
            self._get_all(name, unit.object_path)
        else:  # LoadUnit needs no privilege and gives the object path to read from
            self._t.call(
                MANAGER_PATH,
                MANAGER_IFACE,
                "LoadUnit",
                [name],
                lambda args: self._get_all(name, args[0]),
                self._error_handler(name, "details"),
                signature="s",
            )

    def run(self, action: str, name: str) -> None:
        if action in JOB_METHODS:
            self._set_busy(name, True)
            self._t.call(
                MANAGER_PATH,
                MANAGER_IFACE,
                JOB_METHODS[action],
                [name, "replace"],
                lambda args: self._on_job_started(args[0], name, action),
                self._error_handler(name, action),
                signature="ss",
            )
        elif action in FILE_METHODS:
            method, signature, extra = FILE_METHODS[action]
            self._set_busy(name, True)
            self._t.call(
                MANAGER_PATH,
                MANAGER_IFACE,
                method,
                [[name], *extra],
                # Like systemctl: reload the manager so the change is picked up right away.
                lambda _args: self._reload(name, action),
                self._error_handler(name, action),
                signature=signature,
            )
        elif action in SIMPLE_METHODS:
            self._set_busy(name, True)
            self._t.call(
                MANAGER_PATH,
                MANAGER_IFACE,
                SIMPLE_METHODS[action],
                [name],
                lambda _args: self._finish(name, action, True, ""),
                self._error_handler(name, action),
                signature="s",
            )
        else:
            raise ValueError(f"unknown action {action!r}")

    def daemon_reload(self) -> None:
        self._reload("", "daemon-reload")

    def close(self) -> None:
        self._t.close()

    # ---- replies ----------------------------------------------------------------------------

    def _on_list(self, member: str, rows: list) -> None:
        self._lists[member] = rows
        if len(self._lists) == 2:
            self._merge(self._lists["ListUnits"], self._lists["ListUnitFiles"])

    def _merge(self, rows: list, files: list) -> None:
        file_state: dict[str, str] = {}
        file_path: dict[str, str] = {}
        for path, state in files:
            name = os.path.basename(path)
            if name.endswith(".service"):
                file_state[name] = state
                # Aliases and masks in /etc are symlinks: keep the real file so that they do not
                # count as units created by the user.
                file_path[name] = os.path.realpath(path) if os.path.islink(path) else path
        units: dict[str, Unit] = {}
        for name, description, load, active, sub, _following, path, *_ in rows:
            if not name.endswith(".service"):
                continue
            key = name if name in file_state else template_of(name)
            units[name] = Unit(
                name,
                description,
                load,
                active,
                sub,
                file_state.get(key, ""),
                file_path.get(key, ""),
                path,
            )
        for name, state in file_state.items():  # installed but not loaded
            if name not in units and not name.endswith("@.service"):
                units[name] = Unit(name, unit_file_state=state, fragment_path=file_path[name])
        for name, unit in units.items():
            self._locate(unit)
            old = self.units.get(name)
            if old is not None and old.object_path == unit.object_path:
                unit.can_reload = old.can_reload
                unit.drop_in_paths = old.drop_in_paths
        self.units = units
        self._path_to_name = {u.object_path: n for n, u in units.items() if u.object_path}
        self.units_changed.emit()

    def _get_all(self, name: str, object_path: str) -> None:
        self._t.call(
            object_path,
            PROPERTIES_IFACE,
            "GetAll",
            [UNIT_IFACE],
            lambda args: self._on_details(name, args[0]),
            self._error_handler(name, "details"),
            signature="s",
        )

    def _on_details(self, name: str, props: dict) -> None:
        unit = self.units.get(name)
        if unit is None:
            return
        unit.can_reload = bool(props.get("CanReload", False))
        unit.drop_in_paths = list(props.get("DropInPaths", []))
        _apply(unit, props)
        self._locate(unit)
        self.unit_updated.emit(name)

    def _locate(self, unit: Unit) -> None:
        unit.own = is_own(unit.fragment_path, self.own_dir)
        unit.vendor_path = vendor_copy(unit.name, self.scope) if unit.own else ""

    def _reload(self, name: str, action: str) -> None:
        self._t.call(
            MANAGER_PATH,
            MANAGER_IFACE,
            "Reload",
            [],
            lambda _args: self._finish(name, action, True, ""),
            self._error_handler(name, action),
        )

    # ---- signals from systemd ---------------------------------------------------------------

    def _on_job_started(self, job_path: str, name: str, action: str) -> None:
        # An instant job can be removed before the reply naming it reaches us (the transport
        # delivers signals as they arrive, replies when the caller resumes): settle it now.
        result = self._early_results.pop(job_path, None)
        if result is None:
            self._jobs[job_path] = (name, action)
        else:
            self._job_done(name, action, result)

    def _on_job_removed(self, _path: str, args: list) -> None:
        _job_id, job_path, _unit, result = args
        pending = self._jobs.pop(job_path, None)
        if pending is None:
            self._early_results[job_path] = result
            if len(self._early_results) > 64:  # jobs of other clients: keep the dict small
                self._early_results.pop(next(iter(self._early_results)))
            return
        self._job_done(pending[0], pending[1], result)

    def _job_done(self, name: str, action: str, result: str) -> None:
        unit = self.units.get(name)
        if result != "failed" or unit is None or not unit.loaded:
            self._finish(name, action, result == "done", result)
            return
        # "failed" alone says little: ask the service why (exit-code, start-limit-hit, ...).
        self._t.call(
            unit.object_path,
            PROPERTIES_IFACE,
            "Get",
            [SERVICE_IFACE, "Result"],
            lambda args: self._finish(name, action, False, f"failed ({args[0]})"),
            lambda _error, _message: self._finish(name, action, False, result),
            signature="ss",
        )

    def _on_properties_changed(self, path: str, args: list) -> None:
        interface, changed, _invalidated = args
        name = self._path_to_name.get(path)
        if name is None or interface != UNIT_IFACE or not PROPERTY_FIELDS.keys() & changed.keys():
            return
        _apply(self.units[name], changed)
        self.unit_updated.emit(name)

    def _on_reloading(self, _path: str, args: list) -> None:
        if not args[0]:  # daemon-reload finished
            self._schedule_refresh()

    def _schedule_refresh(self, *_args: object) -> None:
        """Coalesce bursts of UnitNew/UnitRemoved into one refresh."""
        if self._refresh_pending:
            return
        self._refresh_pending = True
        self.runtime.schedule(REFRESH_DEBOUNCE_MS, self._scheduled_refresh)

    def _scheduled_refresh(self) -> None:
        self._refresh_pending = False
        self.refresh()

    # ---- bookkeeping ------------------------------------------------------------------------

    def _set_busy(self, name: str, busy: bool) -> None:
        if not name:
            return
        (self.busy.add if busy else self.busy.discard)(name)
        self.busy_changed.emit(name, busy)

    def _finish(self, name: str, action: str, ok: bool, detail: str) -> None:
        self._set_busy(name, False)
        self.operation_finished.emit(name, action, ok, detail)

    def _error_handler(self, name: str, action: str):
        return lambda error, message: self._finish(name, action, False, f"{error}: {message}")


def _apply(unit: Unit, props: dict) -> None:
    for key, attr in PROPERTY_FIELDS.items():
        if key in props:
            setattr(unit, attr, props[key])


def _ignore(*_args: object) -> None:
    pass


class UserBackend(DBusBackend):
    """Session bus: no authentication involved, files written directly."""

    def __init__(self, runtime: Runtime) -> None:
        super().__init__(Scope.USER, runtime.transport("session"), runtime)
        self.writer = UserWriter(self)


class SystemBackend(DBusBackend):
    """System bus: interactive authorization makes systemd ask polkit; files through the helper."""

    def __init__(self, runtime: Runtime) -> None:
        super().__init__(Scope.SYSTEM, runtime.transport("system", interactive=True), runtime)
        self.writer = HelperWriter(self)
