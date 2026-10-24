# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Nicola Palmieri (n1c0p)
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
    "System services": "Servizi di sistema",
    "User services": "Servizi utente",
    "Ready": "Pronto",
    "System": "Sistema",
    "Language": "Lingua",
    "Settings": "Impostazioni",
    "Check for updates at startup": "Controlla aggiornamenti all'avvio",
    "Info": "Informazioni",
    "Check for updates…": "Controlla aggiornamenti…",
    "About UnitDeck…": "Informazioni su UnitDeck…",
    "About Qt…": "Informazioni su Qt…",
    "About UnitDeck": "Informazioni su UnitDeck",
    "Version {version}": "Versione {version}",
    "A desktop application to manage systemd system and user services.": (
        "Un'applicazione desktop per gestire i servizi systemd di sistema e utente."
    ),
    "Licensed under the GNU GPL, version 3 or later.": (
        "Rilasciato sotto licenza GNU GPL, versione 3 o successiva."
    ),
    # updates
    "Checking for updates…": "Controllo aggiornamenti…",
    "Update available": "Aggiornamento disponibile",
    "UnitDeck is up to date ({version}).": "UnitDeck è aggiornato ({version}).",
    "Update check failed: {error}": "Controllo aggiornamenti non riuscito: {error}",
    "UnitDeck {new} is available (installed: {old}).": (
        "È disponibile UnitDeck {new} (installata: {old})."
    ),
    "No release notes.": "Nessuna nota di rilascio.",
    "No package for this system in the release.": (
        "Nessun pacchetto per questo sistema nella release."
    ),
    "Download and install": "Scarica e installa",
    "Open release page": "Apri la pagina della release",
    "Later": "Più tardi",
    "Downloading…": "Download in corso…",
    "Download failed: {error}": "Download non riuscito: {error}",
    "Checksum mismatch, the downloaded file was discarded.": (
        "Checksum non corrispondente, il file scaricato è stato eliminato."
    ),
    "Installing… the system will ask for your password.": (
        "Installazione in corso… il sistema chiederà la password."
    ),
    "Installed. Restart UnitDeck to use the new version.": (
        "Installato. Riavvia UnitDeck per usare la nuova versione."
    ),
    "Installation failed.": "Installazione non riuscita.",
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
    "Reset failed state": "Azzera lo stato fallito",
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
    "start requests repeated too quickly, wait ten seconds and start it again": (
        "richieste di avvio troppo ravvicinate, aspetta dieci secondi e riavvialo"
    ),
    "the process exited with an error code, check its logs": (
        "il processo è terminato con un codice di errore, controlla i log"
    ),
    "the process was killed by a signal, check its logs": (
        "il processo è stato terminato da un segnale, controlla i log"
    ),
    "the process crashed (core dump), check its logs": (
        "il processo è andato in crash (core dump), controlla i log"
    ),
    "the process did not start or stop within the timeout": (
        "il processo non è partito o non si è fermato entro il timeout"
    ),
    "the watchdog timeout was hit": "è scattato il timeout del watchdog",
    "the process was killed for lack of memory": (
        "il processo è stato terminato per mancanza di memoria"
    ),
    "a resource limit could not be applied": "non è stato possibile applicare un limite di risorse",
    "the service did not follow the notification protocol": (
        "il servizio non ha rispettato il protocollo di notifica"
    ),
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
