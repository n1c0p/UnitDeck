# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Nicola Palmieri (n1c0p)
"""Human-readable labels and reasons shared by the desktop and terminal interfaces."""

from __future__ import annotations

from unitdeck.backend.unitfiles import HELPER_MISSING
from unitdeck.i18n import tr

ACTION_LABELS = {  # source strings, translate with tr() at use time
    "start": "Start",
    "stop": "Stop",
    "restart": "Restart",
    "reload": "Reload",
    "enable": "Enable at boot",
    "disable": "Disable at boot",
    "mask": "Mask",
    "unmask": "Unmask",
    "reset-failed": "Reset failed state",
    "edit": "Edit",
    "revert": "Restore original",
    "delete": "Delete",
    "save": "Save",
    "logs": "Show logs",
    "daemon-reload": "Reload configuration",
    "refresh": "Refresh unit list",
    "details": "Read details",
}
JOB_RESULTS = {  # systemd job results other than "done"
    "failed": "the service failed, check its logs",
    "timeout": "timed out",
    "canceled": "operation cancelled",
    "dependency": "a dependency failed",
    "skipped": "operation skipped (condition not met)",
    "invalid": "operation not valid in the current state",
    "assert": "unit assertion not met",
    "unsupported": "operation not supported",
}
SERVICE_RESULTS = {  # Result property of a failed service
    "start-limit-hit": "start requests repeated too quickly, wait ten seconds and start it again",
    "exit-code": "the process exited with an error code, check its logs",
    "signal": "the process was killed by a signal, check its logs",
    "core-dump": "the process crashed (core dump), check its logs",
    "timeout": "the process did not start or stop within the timeout",
    "watchdog": "the watchdog timeout was hit",
    "oom-kill": "the process was killed for lack of memory",
    "resources": "a resource limit could not be applied",
    "protocol": "the service did not follow the notification protocol",
}
AUTH_ERRORS = (  # polkit dialog cancelled or password refused: status bar only, no popup
    "org.freedesktop.DBus.Error.AccessDenied",
    "org.freedesktop.DBus.Error.InteractiveAuthorizationRequired",
)
ERROR_LABELS = {  # D-Bus error names
    AUTH_ERRORS[0]: "authorization denied",
    AUTH_ERRORS[1]: "authorization required",
    "org.freedesktop.DBus.Error.NoReply": "systemd did not answer in time",
    "org.freedesktop.systemd1.NoSuchUnit": "unit not found",
    "org.freedesktop.systemd1.UnitMasked": "the unit is masked",
    "org.freedesktop.systemd1.JobTypeNotApplicable": "operation not applicable to this unit",
    HELPER_MISSING: "the privileged helper is not installed (see CONTRIBUTING)",
}


def readable(detail: str) -> str:
    """Human-readable, translated reason for a failed operation."""
    if detail in JOB_RESULTS:
        return tr(JOB_RESULTS[detail])
    if detail.startswith("failed (") and detail.endswith(")"):
        result = detail[8:-1]
        return (
            tr(SERVICE_RESULTS[result])
            if result in SERVICE_RESULTS
            else f"{tr(JOB_RESULTS['failed'])} ({result})"
        )
    name, _, message = detail.partition(": ")
    if name in ERROR_LABELS:
        return tr(ERROR_LABELS[name])
    return message or detail
