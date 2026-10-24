# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Nicola Palmieri (n1c0p)
import pytest
from PyQt6.QtCore import QCoreApplication


@pytest.fixture(scope="session", autouse=True)
def qt_app():
    """Qt models and timers need an application object; no event loop is run."""
    return QCoreApplication.instance() or QCoreApplication([])
