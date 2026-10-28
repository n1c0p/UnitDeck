# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Nicola Palmieri (n1c0p)
"""Catalogue of the service directives the form editor knows, and their value checks.

Not every systemd directive is here: the others are still read, kept and written back, shown
as plain text fields with a warning. ``info`` is an English source string, translated with
tr() where it is shown. Checks only flag a value, they never block saving:
``systemd-analyze verify`` stays the final word.
"""

from __future__ import annotations

import difflib
import grp
import pwd
import re
from dataclasses import dataclass

from unitdeck.i18n import tr

SECTIONS = ("Unit", "Service", "Install")
UNIT, SERVICE, EXEC, KILL, RESOURCES = (
    "systemd.unit(5)",
    "systemd.service(5)",
    "systemd.exec(5)",
    "systemd.kill(5)",
    "systemd.resource-control(5)",
)
TRUE = ("1", "yes", "y", "true", "t", "on")
FALSE = ("0", "no", "n", "false", "f", "off")
TIME_UNITS = (
    "usec|us|µs|msec|ms|seconds|second|sec|s|minutes|minute|min|m|hours|hour|hr|h"
    "|days|day|d|weeks|week|w|months|month|M|years|year|y"
)
TIME_SPAN = re.compile(rf"^(infinity|(\d+(\.\d+)?\s*({TIME_UNITS})?\s*)+)$")
PATH = re.compile(r"^[-!|+]*[/~%]")


@dataclass(frozen=True, slots=True)
class Directive:
    section: str
    key: str
    info: str
    example: str
    man: str
    kind: str = "text"  # text | enum | bool | time | path | paths | user | group
    choices: tuple[str, ...] = ()
    repeatable: bool = False


def _d(section, key, info, example, man, kind="text", choices=(), repeatable=False):
    return Directive(section, key, info, example, man, kind, tuple(choices), repeatable)


def _bool(section, key, info, man):
    return _d(section, key, info, "yes", man, "bool")


# fmt: off
CATALOG = [
    # [Unit]
    _d("Unit", "Description",
       "Short human-readable name of the unit, shown by systemctl and in the logs.",
       "Foo backup daemon", UNIT),
    _d("Unit", "Documentation",
       "URIs of the documentation for this unit: http(s)://, file:, info: or man:.",
       "man:foo(8) https://example.org/foo", UNIT, repeatable=True),
    _d("Unit", "Wants",
       "Weak dependency: start the listed units too, but do not fail if they fail.",
       "network-online.target", UNIT, repeatable=True),
    _d("Unit", "Requires",
       "Strong dependency: start the listed units too; if one fails to start or is stopped, "
       "this unit is stopped as well.",
       "postgresql.service", UNIT, repeatable=True),
    _d("Unit", "Requisite",
       "Like Requires=, but the listed units must already be active: they are not started.",
       "postgresql.service", UNIT, repeatable=True),
    _d("Unit", "BindsTo",
       "Like Requires=, and this unit also stops whenever a listed unit stops, even by itself.",
       "dev-sdb1.device", UNIT, repeatable=True),
    _d("Unit", "PartOf",
       "Stopping or restarting a listed unit stops or restarts this unit too (one way only).",
       "foo.target", UNIT, repeatable=True),
    _d("Unit", "Conflicts",
       "Starting this unit stops the listed units, and the other way round.",
       "shutdown.target", UNIT, repeatable=True),
    _d("Unit", "After",
       "Start this unit after the listed units have finished starting. Ordering only: it does "
       "not pull them in, combine it with Wants= or Requires=.",
       "network-online.target", UNIT, repeatable=True),
    _d("Unit", "Before",
       "Start this unit before the listed units. Ordering only.",
       "nginx.service", UNIT, repeatable=True),
    _d("Unit", "OnFailure",
       "Units started when this unit enters the failed state, for example to send a notice.",
       "notify-failure@%n.service", UNIT, repeatable=True),
    _d("Unit", "ConditionPathExists",
       "Start only if the path exists (prefix it with ! to require that it does not). When the "
       "check fails the unit is skipped, not failed.",
       "/etc/foo/foo.conf", UNIT, "path", repeatable=True),
    _d("Unit", "ConditionPathIsDirectory",
       "Start only if the path exists and is a directory. When the check fails the unit is "
       "skipped.",
       "/srv/foo", UNIT, "path", repeatable=True),
    _d("Unit", "ConditionFileNotEmpty",
       "Start only if the path is a regular file that is not empty.",
       "/etc/foo/foo.conf", UNIT, "path", repeatable=True),
    _d("Unit", "AssertPathExists",
       "Like ConditionPathExists=, but a failed check makes the start fail with an error.",
       "/etc/foo/foo.conf", UNIT, "path", repeatable=True),
    _d("Unit", "StartLimitIntervalSec",
       "Time window of the start rate limit: at most StartLimitBurst= starts are allowed in it. "
       "0 disables the limit.",
       "60s", UNIT, "time"),
    _d("Unit", "StartLimitBurst",
       "Number of starts allowed within StartLimitIntervalSec=.",
       "5", UNIT),
    _d("Unit", "JobTimeoutSec",
       "Maximum time a start or stop job of this unit may wait in the queue and run.",
       "5min", UNIT, "time"),
    _bool("Unit", "DefaultDependencies",
          "Add the usual dependencies on basic system targets. Turn off only for early boot or "
          "late shutdown units.", UNIT),
    _bool("Unit", "StopWhenUnneeded",
          "Stop this unit automatically when no other active unit needs it.", UNIT),
    _bool("Unit", "RefuseManualStart",
          "Refuse a start requested directly by the user: only dependencies may start it.", UNIT),
    _bool("Unit", "RefuseManualStop",
          "Refuse a stop requested directly by the user.", UNIT),
    # [Service]: start-up and commands
    _d("Service", "Type",
       "When systemd considers the service started. simple: right after fork; exec: once the "
       "binary runs; forking: when the parent exits; oneshot: when the process exits; dbus: when "
       "BusName= appears on the bus; notify: when it sends READY=1; idle: like simple, after "
       "other jobs finish.",
       "simple", SERVICE, "enum",
       ("simple", "exec", "forking", "oneshot", "dbus", "notify", "notify-reload", "idle")),
    _bool("Service", "RemainAfterExit",
          "Keep the service active after all its processes exit. Typical with Type=oneshot.",
          SERVICE),
    _d("Service", "ExecStart",
       "Command that starts the service: absolute path, or a command in the default PATH. Only "
       "Type=oneshot accepts more than one. In a drop-in, an empty ExecStart= first clears the "
       "list.",
       "/usr/bin/foo --config /etc/foo.conf", SERVICE, repeatable=True),
    _d("Service", "ExecStartPre",
       "Commands run before ExecStart=. Prefix with - to ignore their failure.",
       "-/usr/bin/mkdir -p /run/foo", SERVICE, repeatable=True),
    _d("Service", "ExecStartPost",
       "Commands run after the service has started.",
       "/usr/bin/foo-ctl announce", SERVICE, repeatable=True),
    _d("Service", "ExecCondition",
       "Commands run before ExecStartPre=: exit code 1 to 254 skips the start without an error, "
       "255 fails it.",
       "/usr/bin/test -f /etc/foo/enabled", SERVICE, repeatable=True),
    _d("Service", "ExecReload",
       "Command run by systemctl reload.",
       "/bin/kill -HUP $MAINPID", SERVICE, repeatable=True),
    _d("Service", "ExecStop",
       "Command that stops the service. Without it, the processes get KillSignal=.",
       "/usr/bin/foo --shutdown", SERVICE, repeatable=True),
    _d("Service", "ExecStopPost",
       "Commands run after the service stopped, also when it failed.",
       "/usr/bin/rm -f /run/foo/lock", SERVICE, repeatable=True),
    _d("Service", "PIDFile",
       "File where a Type=forking service writes the PID of its main process.",
       "/run/foo.pid", SERVICE, "path"),
    _d("Service", "BusName",
       "D-Bus name the service acquires. Required with Type=dbus.",
       "org.example.Foo", SERVICE),
    _d("Service", "NotifyAccess",
       "Which processes may send status notifications (sd_notify) for the service.",
       "main", SERVICE, "enum", ("none", "main", "exec", "all")),
    # [Service]: restart and timeouts
    _d("Service", "Restart",
       "When to restart the service after its process exits, is killed or times out.",
       "on-failure", SERVICE, "enum",
       ("no", "on-success", "on-failure", "on-abnormal", "on-watchdog", "on-abort", "always")),
    _d("Service", "RestartSec",
       "Time to wait before restarting the service.",
       "5s", SERVICE, "time"),
    _d("Service", "SuccessExitStatus",
       "Extra exit codes and signals that count as a clean exit.",
       "143 SIGTERM", SERVICE, repeatable=True),
    _d("Service", "RestartPreventExitStatus",
       "Exit codes and signals that never trigger a restart.",
       "2 SIGKILL", SERVICE, repeatable=True),
    _d("Service", "TimeoutStartSec",
       "Maximum start-up time; past it the service is considered failed. infinity disables the "
       "timeout.",
       "90s", SERVICE, "time"),
    _d("Service", "TimeoutStopSec",
       "Maximum time to wait for the stop; past it the processes get SIGKILL.",
       "30s", SERVICE, "time"),
    _d("Service", "TimeoutSec",
       "Sets both TimeoutStartSec= and TimeoutStopSec=.",
       "2min", SERVICE, "time"),
    _d("Service", "RuntimeMaxSec",
       "Maximum running time: past it the service is stopped and counted as failed.",
       "1h", SERVICE, "time"),
    _d("Service", "WatchdogSec",
       "The service must send WATCHDOG=1 at least this often, or it is considered failed.",
       "30s", SERVICE, "time"),
    # [Service]: how processes are killed
    _d("Service", "KillMode",
       "Which processes are killed on stop: the whole control group, the main process first "
       "and then the rest (mixed), only the main process, or none.",
       "control-group", KILL, "enum", ("control-group", "mixed", "process", "none")),
    _d("Service", "KillSignal",
       "Signal sent to stop the service.",
       "SIGTERM", KILL),
    _bool("Service", "SendSIGKILL",
          "Send SIGKILL to processes still running after TimeoutStopSec=.", KILL),
    # [Service]: execution environment
    _d("Service", "WorkingDirectory",
       "Working directory of the processes. ~ means the home of User=; a - prefix ignores a "
       "missing directory.",
       "/srv/foo", EXEC, "path"),
    _d("Service", "RootDirectory",
       "Run the processes with this directory as root (chroot).",
       "/srv/foo/root", EXEC, "path"),
    _d("Service", "User",
       "User the processes run as (name or UID). System services only: user services already "
       "run as you.",
       "foo", EXEC, "user"),
    _d("Service", "Group",
       "Group the processes run as.",
       "foo", EXEC, "group"),
    _bool("Service", "DynamicUser",
          "Run as a temporary user and group allocated when the service starts.", EXEC),
    _d("Service", "SupplementaryGroups",
       "Extra groups for the processes.",
       "audio video", EXEC, repeatable=True),
    _d("Service", "UMask",
       "File mode creation mask of the processes, in octal.",
       "0027", EXEC),
    _d("Service", "Environment",
       "Environment variables as KEY=value, separated by spaces. Quote assignments that contain "
       "spaces.",
       'LANG=C "GREETING=hello world"', EXEC, repeatable=True),
    _d("Service", "EnvironmentFile",
       "File with KEY=value lines to read variables from. Prefix with - to ignore a missing file.",
       "-/etc/default/foo", EXEC, "path", repeatable=True),
    _d("Service", "PassEnvironment",
       "Names of variables passed on from the service manager's own environment.",
       "TZ LANG", EXEC, repeatable=True),
    _d("Service", "StandardOutput",
       "Where standard output goes: journal, null, inherit, tty, file:path, append:path, "
       "truncate:path, socket.",
       "journal", EXEC),
    _d("Service", "StandardError",
       "Where standard error goes; same values as StandardOutput=.",
       "journal", EXEC),
    _d("Service", "StandardInput",
       "Where standard input comes from: null, tty, tty-force, tty-fail, data, file:path, socket.",
       "null", EXEC),
    _d("Service", "SyslogIdentifier",
       "Name used for the messages of the service in the journal.",
       "foo", EXEC),
    _d("Service", "Nice",
       "Scheduling priority, from -20 (highest) to 19 (lowest).",
       "10", EXEC),
    _d("Service", "LimitNOFILE",
       "Maximum number of open files: one value, or soft:hard.",
       "65536", EXEC),
    _d("Service", "LimitNPROC",
       "Maximum number of processes of the user.",
       "512", EXEC),
    _d("Service", "RuntimeDirectory",
       "Directories created under /run (or $XDG_RUNTIME_DIR for user services) when the service "
       "starts, owned by it and removed when it stops.",
       "foo", EXEC, repeatable=True),
    _d("Service", "StateDirectory",
       "Directories created under /var/lib (or ~/.local/state) for persistent data, owned by the "
       "service.",
       "foo", EXEC, repeatable=True),
    _d("Service", "CacheDirectory",
       "Directories created under /var/cache (or ~/.cache), owned by the service.",
       "foo", EXEC, repeatable=True),
    _d("Service", "LogsDirectory",
       "Directories created under /var/log, owned by the service.",
       "foo", EXEC, repeatable=True),
    _d("Service", "ConfigurationDirectory",
       "Directories created under /etc (or ~/.config) for the configuration of the service.",
       "foo", EXEC, repeatable=True),
    # [Service]: sandboxing
    _d("Service", "ProtectSystem",
       "Mount read-only for the service: /usr and /boot (yes), also /etc (full), or the whole "
       "file system except /dev, /proc and /sys (strict).",
       "strict", EXEC, "enum", ("no", "yes", "full", "strict")),
    _d("Service", "ProtectHome",
       "Make /home, /root and /run/user inaccessible (yes), read-only, or empty (tmpfs).",
       "read-only", EXEC, "enum", ("no", "yes", "read-only", "tmpfs")),
    _bool("Service", "PrivateTmp",
          "Give the service its own private /tmp and /var/tmp.", EXEC),
    _bool("Service", "PrivateDevices",
          "Give the service a minimal /dev without physical devices.", EXEC),
    _bool("Service", "PrivateNetwork",
          "Run the service in its own network namespace with only a loopback interface.", EXEC),
    _bool("Service", "NoNewPrivileges",
          "Prevent the processes and their children from gaining privileges, for example "
          "through setuid binaries.", EXEC),
    _bool("Service", "ProtectKernelTunables",
          "Make /proc/sys, /sys and similar kernel settings read-only.", EXEC),
    _bool("Service", "ProtectKernelModules",
          "Forbid loading and unloading kernel modules.", EXEC),
    _d("Service", "ReadWritePaths",
       "Paths left writable when ProtectSystem= makes the rest read-only.",
       "/var/lib/foo /run/foo", EXEC, "paths", repeatable=True),
    _d("Service", "ReadOnlyPaths",
       "Paths made read-only for the service.",
       "/etc/foo", EXEC, "paths", repeatable=True),
    _d("Service", "InaccessiblePaths",
       "Paths made completely inaccessible for the service.",
       "/home /root", EXEC, "paths", repeatable=True),
    _d("Service", "CapabilityBoundingSet",
       "Capabilities the processes may ever hold; prefix with ~ to list the ones to drop.",
       "CAP_NET_BIND_SERVICE", EXEC, repeatable=True),
    _d("Service", "AmbientCapabilities",
       "Capabilities granted to the processes even when they run as an unprivileged user.",
       "CAP_NET_BIND_SERVICE", EXEC, repeatable=True),
    # [Service]: resources
    _d("Service", "MemoryHigh",
       "Memory throttling limit: above it the processes are slowed down and memory is reclaimed.",
       "400M", RESOURCES),
    _d("Service", "MemoryMax",
       "Hard memory limit: above it the OOM killer acts. Bytes with K/M/G/T suffix, a "
       "percentage of RAM, or infinity.",
       "512M", RESOURCES),
    _d("Service", "CPUQuota",
       "Maximum CPU time relative to one CPU: 200% means two whole CPUs.",
       "50%", RESOURCES),
    _d("Service", "CPUWeight",
       "Relative share of CPU time, from 1 to 10000 (default 100).",
       "50", RESOURCES),
    _d("Service", "IOWeight",
       "Relative share of disk I/O, from 1 to 10000 (default 100).",
       "50", RESOURCES),
    _d("Service", "TasksMax",
       "Maximum number of processes and threads, or a percentage of the system limit.",
       "64", RESOURCES),
    _d("Service", "OOMScoreAdjust",
       "How likely the kernel is to kill the processes when memory runs out, from -1000 (never) "
       "to 1000.",
       "500", EXEC),
    _d("Service", "Slice",
       "Slice (resource group) the service is placed in.",
       "background.slice", RESOURCES),
    # [Install]
    _d("Install", "WantedBy",
       "When enabled, the unit starts together with the listed target (a symlink in its .wants/ "
       "directory). Usually multi-user.target, or default.target for user units.",
       "multi-user.target", UNIT, repeatable=True),
    _d("Install", "RequiredBy",
       "Like WantedBy=, but creates a Requires= dependency (.requires/ directory).",
       "foo.target", UNIT, repeatable=True),
    _d("Install", "UpheldBy",
       "When enabled, the listed units keep this unit running, restarting it if it stops.",
       "foo.target", UNIT, repeatable=True),
    _d("Install", "Alias",
       "Additional names for the unit, created as symlinks when enabled.",
       "bar.service", UNIT, repeatable=True),
    _d("Install", "Also",
       "Other units enabled and disabled together with this one.",
       "foo.socket", UNIT, repeatable=True),
    _d("Install", "DefaultInstance",
       "For a template unit (name@.service): the instance enabled when none is given.",
       "main", UNIT),
]
# fmt: on
BY_KEY = {(d.section, d.key): d for d in CATALOG}


def lookup(section: str, key: str) -> Directive | None:
    return BY_KEY.get((section, key))


def unknown(section: str, key: str) -> Directive:
    """Stand-in for a directive missing from the catalogue: plain text, repeatable."""
    return Directive(section, key, "", "", "systemd.directives(7)", repeatable=True)


def parse_bool(value: str) -> bool | None:
    lowered = value.strip().lower()
    return True if lowered in TRUE else False if lowered in FALSE else None


def initial_value(directive: Directive) -> str:
    """Value of a freshly added row: the example for a choice, empty for free text."""
    return directive.example if directive.kind in ("enum", "bool") else ""


def bool_value(checked: bool, orig: str | None) -> str:
    """A checkbox state as text, keeping the file's own spelling (true, on, 1...) if unchanged."""
    if orig is not None and parse_bool(orig) == checked:
        return orig
    return "yes" if checked else "no"


def fits_widget(directive: Directive, value: str) -> bool:
    """Whether ``value`` can be shown by the directive's typed widget (else: a text field)."""
    if "\n" in value:
        return False
    if directive.kind == "bool":
        return parse_bool(value) is not None
    if directive.kind == "enum":
        return value in directive.choices
    return True


def problem(directive: Directive, value: str) -> str:
    """'' when the value looks right, else a short reason. Empty values reset: always fine."""
    value = value.strip()
    if not directive.info:
        close = difflib.get_close_matches(
            directive.key, [d.key for d in CATALOG if d.section == directive.section], 1, 0.8
        )
        hint = " " + tr("Did you mean {key}?").format(key=close[0]) if close else ""
        return tr("Not in UnitDeck's catalogue.") + hint
    if not value or "\n" in value:
        return ""
    kind = directive.kind
    if kind == "bool" and parse_bool(value) is None:
        return tr("Expected yes or no.")
    if (
        kind == "enum"
        and value not in directive.choices
        and ("yes" not in directive.choices or parse_bool(value) is None)
    ):
        return tr("Expected one of: {values}.").format(values=", ".join(directive.choices))
    if kind == "time" and not TIME_SPAN.match(value):
        return tr("Expected a time span such as 5s, 2min 30s or infinity.")
    if kind in ("path", "paths"):
        tokens = value.split() if kind == "paths" else [value]
        if not all(PATH.match(token) for token in tokens):
            return tr("Expected an absolute path.")
    if kind in ("user", "group") and not value.isdigit() and "%" not in value:
        try:
            (pwd.getpwnam if kind == "user" else grp.getgrnam)(value)
        except KeyError:
            if kind == "user":
                return tr("No user named {name} on this system.").format(name=value)
            return tr("No group named {name} on this system.").format(name=value)
    return ""
