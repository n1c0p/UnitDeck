# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Nicola Palmieri (n1c0p)
from PyQt6.QtCore import Qt

from unitdeck.backend.base import Scope, SystemdBackend, Unit
from unitdeck.model import ACTIVE, NAME, StateFilter, UnitModel, UnitProxy


class StaticBackend(SystemdBackend):
    def __init__(self, units):
        super().__init__(Scope.USER)
        self.units = {u.name: u for u in units}


def names(proxy):
    return [proxy.index(row, NAME).data() for row in range(proxy.rowCount())]


def make():
    backend = StaticBackend(
        [
            Unit(
                "beta.service",
                "Second",
                "loaded",
                "active",
                "running",
                "enabled",
                "/usr/lib/systemd/user/beta.service",
                "/b",
            ),
            Unit(
                "alpha.service",
                "First one",
                "loaded",
                "failed",
                "failed",
                "disabled",
                "/usr/lib/systemd/user/alpha.service",
                "/a",
            ),
            Unit(
                "mine.service",
                "",
                "",
                "inactive",
                "dead",
                "disabled",
                "/home/me/.config/systemd/user/mine.service",
                "",
            ),
        ]
    )
    model = UnitModel(backend)
    backend.units_changed.emit()
    proxy = UnitProxy("/home/me/.config/systemd/user")
    proxy.setSourceModel(model)
    proxy.sort(NAME, Qt.SortOrder.AscendingOrder)
    return backend, model, proxy


def test_model_rows_and_state_text():
    _, model, proxy = make()
    assert names(proxy) == ["alpha.service", "beta.service", "mine.service"]
    assert proxy.index(0, ACTIVE).data() == "failed (failed)"
    assert proxy.index(2, ACTIVE).data() == "inactive"  # not loaded


def test_text_and_state_filters():
    backend, _, proxy = make()
    proxy.set_text("FIRST")
    assert names(proxy) == ["alpha.service"]
    proxy.set_text("")
    proxy.set_state(StateFilter.FAILED)
    assert names(proxy) == ["alpha.service"]
    proxy.set_state(StateFilter.ACTIVE)
    assert names(proxy) == ["beta.service"]
    backend.units["mine.service"].active_state = "activating"
    backend.units_changed.emit()
    assert names(proxy) == ["beta.service", "mine.service"]  # transitions stay visible
    proxy.set_state(StateFilter.MINE)
    assert names(proxy) == ["mine.service"]


def test_in_place_update_keeps_rows():
    backend, model, proxy = make()
    reset = []
    model.modelReset.connect(lambda: reset.append(True))
    backend.units["beta.service"].active_state = "inactive"
    backend.units_changed.emit()  # same names: no reset
    assert reset == [] and proxy.index(1, ACTIVE).data() == "inactive (running)"
    del backend.units["mine.service"]
    backend.units_changed.emit()
    assert reset == [True] and names(proxy) == ["alpha.service", "beta.service"]
