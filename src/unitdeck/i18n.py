# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Nicola Palmieri (n1c0p)
"""Tiny translation layer: English source strings, Italian catalogue, no build step.

Call ``tr("text")`` at use time (not at import time) so a language change takes effect when
widgets are rebuilt. Strings with ``{placeholders}`` are formatted by the caller.
"""

from __future__ import annotations

import locale
import os

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
    candidates = [os.environ.get(var, "") for var in ("LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG")]
    try:
        candidates.append(locale.getlocale()[0] or "")
    except ValueError:
        pass
    for name in candidates:
        for item in name.split(":"):
            language = item.split("_")[0].split("-")[0].split(".")[0]
            if language in CATALOGUES:
                return language
            if language and language != "C":
                return "en"
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
    "Restart UnitDeck": "Riavvia UnitDeck",
    "Could not start the new version, please restart UnitDeck.": (
        "Impossibile avviare la nuova versione, riavvia UnitDeck."
    ),
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
    "New service": "Nuovo servizio",
    "Linger": "Linger",
    "Keep user services running without an open session (loginctl enable-linger)": (
        "Mantiene i servizi utente in esecuzione senza una sessione aperta (loginctl enable-linger)"
    ),
    "{action}: {reason}": "{action}: {reason}",
    # terminal interface
    "Connecting…": "Connessione…",
    "Filter": "Filtro",
    "last {n} lines": "ultime {n} righe",
    # new service wizard
    "Name and template": "Nome e template",
    "Service name:": "Nome del servizio:",
    "my-service": "mio-servizio",
    "Template:": "Template:",
    "Use letters, digits, '-', '_', '.' and ':' only.": (
        "Usa solo lettere, cifre, '-', '_', '.' e ':'."
    ),
    "A unit with this name already exists.": "Esiste già una unit con questo nome.",
    "Guided fields": "Campi guidati",
    "Type": "Tipo",
    "Command (ExecStart)": "Comando (ExecStart)",
    "Stop command (ExecStop)": "Comando di arresto (ExecStop)",
    "Restart policy (Restart)": "Politica di riavvio (Restart)",
    "Start after (After)": "Avvia dopo (After)",
    "Wants": "Richiede (Wants)",
    "User": "Utente",
    "Group": "Gruppo",
    "Wanted by (WantedBy)": "Richiesto da (WantedBy)",
    "Server": "Server",
    "Share": "Condivisione",
    "Credentials file (relative to home)": "File delle credenziali (relativo alla home)",
    "Without User= and Group= the service runs as root.": (
        "Senza User= e Group= il servizio gira come root."
    ),
    "Preview": "Anteprima",
    "Generated unit file, editable by hand:": "File unit generato, modificabile a mano:",
    "Final options": "Opzioni finali",
    "Start now": "Avvia subito",
    "The unit will be written to {path}.": "La unit verrà scritta in {path}.",
    "The system will ask for your password.": "Il sistema chiederà la password.",
    # template names
    "Empty service": "Servizio vuoto",
    "One-shot task (RemainAfterExit)": "Attività oneshot (RemainAfterExit)",
    "Long-running service (Restart=on-failure)": "Servizio long-running (Restart=on-failure)",
    "SMB share mounted with gio": "Condivisione SMB montata con gio",
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
    "Edit": "Modifica",
    "Restore original": "Ripristina originale",
    "Delete": "Elimina",
    "Save": "Salva",
    "the privileged helper is not installed (see CONTRIBUTING)": (
        "l'helper privilegiato non è installato (vedi CONTRIBUTING)"
    ),
    "Remove every drop-in and local copy of {unit} and go back to the package version?": (
        "Rimuovere tutti i drop-in e le copie locali di {unit} "
        "e tornare alla versione del pacchetto?"
    ),
    "Delete the unit file of {unit}? This cannot be undone.": (
        "Eliminare il file unit di {unit}? L'operazione non si può annullare."
    ),
    "{unit} is running. Restart it now to apply the new configuration?": (
        "{unit} è in esecuzione. Riavviarlo adesso per applicare la nuova configurazione?"
    ),
    # editor
    "Edit – {unit}": "Modifica – {unit}",
    "Drop-in for {unit}: only the directives to change go here.": (
        "Drop-in per {unit}: qui vanno solo le direttive da cambiare."
    ),
    "To replace a list like ExecStart=, first clear it with an empty ExecStart= line.": (
        "Per sostituire una lista come ExecStart=, prima svuotala con una riga ExecStart= vuota."
    ),
    "Edit a full copy of the unit instead of a drop-in (not recommended)": (
        "Modifica una copia completa della unit invece di un drop-in (sconsigliato)"
    ),
    "Effective configuration (unit file and drop-ins):": (
        "Configurazione effettiva (file unit e drop-in):"
    ),
    "Verify": "Verifica",
    "Cancel": "Annulla",
    "Package unit {path}: saved as the drop-in {dropin}, kept across package upgrades.": (
        "Unit del pacchetto {path}: salvata come drop-in {dropin}, conservato agli aggiornamenti."
    ),
    "A full copy in {dropin} shadows {path}: package upgrades no longer reach it.": (
        "Una copia completa in {dropin} nasconde {path}: "
        "gli aggiornamenti del pacchetto non la toccano più."
    ),
    "Editing {dropin} directly.": "Modifica diretta di {dropin}.",
    "Discard the changes in the editor?": "Scartare le modifiche nell'editor?",
    "Verifying…": "Verifica in corso…",
    "Saving…": "Salvataggio in corso…",
    "systemd-analyze verify: no problems found.": (
        "systemd-analyze verify: nessun problema trovato."
    ),
    "systemd-analyze verify found errors:": "systemd-analyze verify ha trovato errori:",
    "systemd-analyze verify warnings:": "avvisi di systemd-analyze verify:",
    "systemd-analyze verify reported errors. Save anyway?": (
        "systemd-analyze verify ha segnalato errori. Salvare comunque?"
    ),
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
