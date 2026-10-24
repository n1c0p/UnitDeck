# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Nicola (n1c0p)
"""UnitDeck: manage systemd system and user services from a desktop GUI."""

try:
    from unitdeck._version import __version__
except ImportError:  # running from a plain checkout, not installed
    __version__ = "0.0.0+unknown"

APP_ID = "eu.nicop.unitdeck"
