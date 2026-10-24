# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Nicola (n1c0p)
"""Tiny translation layer: English source strings, Italian catalogue, no build step.

Call ``tr("text")`` at use time (not at import time) so a language change takes effect when
widgets are rebuilt. Strings with ``{placeholders}`` are formatted by the caller.
"""

from __future__ import annotations

from PyQt6.QtCore import QLocale

LANGUAGES = ("system", "en", "it")
_current = "en"


def tr(text: str) -> str:
    return CATALOGUES.get(_current, {}).get(text, text)


def language() -> str:
    return _current


def set_language(code: str) -> None:
    """``code`` is one of LANGUAGES; "system" follows the desktop locale."""
    global _current
    _current = resolve(code)


def resolve(code: str) -> str:
    if code != "system":
        return code
    for name in QLocale.system().uiLanguages():
        if name.split("-")[0] in CATALOGUES:
            return name.split("-")[0]
    return "en"


IT = {
    # main window
    "User services": "Servizi utente",
    "Ready": "Pronto",
    "System": "Sistema",
    "Language": "Lingua",
    # table
    "Name": "Nome",
    "Description": "Descrizione",
    "Load": "Caricamento",
    "State": "Stato",
    "Startup": "Avvio automatico",
    "Actions": "Azioni",
    "not loaded": "non caricata",
    "All": "Tutti",
    "Active": "Attivi",
    "Inactive": "Inattivi",
    "Failed": "Falliti",
    "Created by me": "Creati da me",
    "Search by name or description…": "Cerca per nome o descrizione…",
    "Reload configuration": "Ricarica configurazione",
    "daemon-reload: re-read unit files changed on disk": (
        "daemon-reload: rilegge i file unit modificati su disco"
    ),
    "Refresh": "Aggiorna",
    "Re-read the unit list": "Rilegge l'elenco delle unit",
    # actions
    "Start": "Avvia",
    "Stop": "Ferma",
    "Restart": "Riavvia",
    "Reload": "Ricarica",
    "Enable at boot": "Abilita all'avvio",
    "Disable at boot": "Disabilita all'avvio",
    "Mask": "Maschera",
    "Unmask": "Smaschera",
    "Show logs": "Mostra log",
    "More actions": "Altre azioni",
    "Refresh unit list": "Aggiornamento elenco",
    "Read details": "Lettura dettagli",
    "{action} {unit}…": "{action} {unit}…",
    "{action} {unit}: done": "{action} {unit}: completato",
    "{action} {unit}: {reason}": "{action} {unit}: {reason}",
    "{action} {unit} failed:\n{reason}": "{action} {unit} non riuscito:\n{reason}",
    # job results and D-Bus errors
    "the service failed, check its logs": "il servizio ha fallito, controlla i log",
    "timed out": "tempo scaduto",
    "operation cancelled": "operazione annullata",
    "a dependency failed": "una dipendenza ha fallito",
    "operation skipped (condition not met)": "operazione saltata (condizione non soddisfatta)",
    "operation not valid in the current state": "operazione non valida per lo stato attuale",
    "unit assertion not met": "asserzione della unit non soddisfatta",
    "operation not supported": "operazione non supportata",
    "authorization denied": "autorizzazione negata",
    "authorization required": "autorizzazione richiesta",
    "systemd did not answer in time": "systemd non ha risposto in tempo",
    "unit not found": "unit non trovata",
    "the unit is masked": "la unit è mascherata",
    "operation not applicable to this unit": "operazione non applicabile a questa unit",
    # log viewer
    "Logs – {unit}": "Log – {unit}",
    "Priority:": "Priorità:",
    "Show messages with this priority or more severe": (
        "Mostra i messaggi con questa priorità o più grave"
    ),
    "Lines:": "Righe:",
    "Follow (live)": "Segui (live)",
    "No journal entries for this unit.": "Nessuna voce nel journal per questa unit.",
}

CATALOGUES = {"it": IT}
