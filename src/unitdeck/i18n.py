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
    "New service": "Nuovo servizio",
    "Linger": "Linger",
    "Keep user services running without an open session (loginctl enable-linger)": (
        "Mantiene i servizi utente in esecuzione senza una sessione aperta (loginctl enable-linger)"
    ),
    "{action}: {reason}": "{action}: {reason}",
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
    "Service": "Servizio",
    "Fill in the directives, or write the unit file in the Text tab.": (
        "Compila le direttive, oppure scrivi il file unit nella scheda Testo."
    ),
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
    "Effective configuration": "Configurazione effettiva",
    # service editor
    "Builder": "Costruttore",
    "Text": "Testo",
    "Preview of the unit file:": "Anteprima del file unit:",
    "Add": "Aggiungi",
    "Drag to reorder": "Trascina per riordinare",
    "What is this directive for?": "A cosa serve questa direttiva?",
    "Remove this directive": "Rimuovi questa direttiva",
    "enabled": "attivo",
    "Example:": "Esempio:",
    "Values:": "Valori:",
    "Can be set more than once.": "Si può impostare più volte.",
    "UnitDeck has no description for this directive.": (
        "UnitDeck non ha una descrizione per questa direttiva."
    ),
    "Value split over several lines: edit it in the Text tab.": (
        "Valore su più righe: modificalo nella scheda Testo."
    ),
    "Not in UnitDeck's catalogue.": "Non è nel catalogo di UnitDeck.",
    "Did you mean {key}?": "Forse intendevi {key}?",
    "Expected yes or no.": "Atteso yes o no.",
    "Expected one of: {values}.": "Atteso uno tra: {values}.",
    "Expected a time span such as 5s, 2min 30s or infinity.": (
        "Attesa una durata come 5s, 2min 30s o infinity."
    ),
    "Expected an absolute path.": "Atteso un percorso assoluto.",
    "No user named {name} on this system.": "Nessun utente {name} su questo sistema.",
    "No group named {name} on this system.": "Nessun gruppo {name} su questo sistema.",
    # directive catalogue: [Unit]
    "Short human-readable name of the unit, shown by systemctl and in the logs.": (
        "Nome breve e leggibile della unit, mostrato da systemctl e nei log."
    ),
    "URIs of the documentation for this unit: http(s)://, file:, info: or man:.": (
        "URI della documentazione di questa unit: http(s)://, file:, info: o man:."
    ),
    "Weak dependency: start the listed units too, but do not fail if they fail.": (
        "Dipendenza debole: avvia anche le unit indicate, ma non fallire se falliscono."
    ),
    "Strong dependency: start the listed units too; if one fails to start or is stopped, "
    "this unit is stopped as well.": (
        "Dipendenza forte: avvia anche le unit indicate; se una non parte o viene fermata, "
        "si ferma anche questa unit."
    ),
    "Like Requires=, but the listed units must already be active: they are not started.": (
        "Come Requires=, ma le unit indicate devono essere già attive: non vengono avviate."
    ),
    "Like Requires=, and this unit also stops whenever a listed unit stops, even by itself.": (
        "Come Requires=, e in più questa unit si ferma ogni volta che si ferma una unit "
        "indicata, anche da sola."
    ),
    "Stopping or restarting a listed unit stops or restarts this unit too (one way only).": (
        "Fermare o riavviare una unit indicata ferma o riavvia anche questa (in un solo senso)."
    ),
    "Starting this unit stops the listed units, and the other way round.": (
        "Avviare questa unit ferma le unit indicate, e viceversa."
    ),
    "Start this unit after the listed units have finished starting. Ordering only: it does "
    "not pull them in, combine it with Wants= or Requires=.": (
        "Avvia questa unit dopo che le unit indicate hanno finito di avviarsi. Solo ordinamento: "
        "non le avvia, va combinato con Wants= o Requires=."
    ),
    "Start this unit before the listed units. Ordering only.": (
        "Avvia questa unit prima delle unit indicate. Solo ordinamento."
    ),
    "Units started when this unit enters the failed state, for example to send a notice.": (
        "Unit avviate quando questa unit entra nello stato fallito, ad esempio per inviare "
        "un avviso."
    ),
    "Start only if the path exists (prefix it with ! to require that it does not). When the "
    "check fails the unit is skipped, not failed.": (
        "Avvia solo se il percorso esiste (con il prefisso ! richiede che non esista). Se il "
        "controllo non passa la unit viene saltata, non fallisce."
    ),
    "Start only if the path exists and is a directory. When the check fails the unit is skipped.": (
        "Avvia solo se il percorso esiste ed è una directory. Se il controllo non passa la "
        "unit viene saltata."
    ),
    "Start only if the path is a regular file that is not empty.": (
        "Avvia solo se il percorso è un file regolare non vuoto."
    ),
    "Like ConditionPathExists=, but a failed check makes the start fail with an error.": (
        "Come ConditionPathExists=, ma se il controllo non passa l'avvio fallisce con un errore."
    ),
    "Time window of the start rate limit: at most StartLimitBurst= starts are allowed in it. "
    "0 disables the limit.": (
        "Finestra di tempo del limite di avvii: al suo interno sono permessi al massimo "
        "StartLimitBurst= avvii. 0 disattiva il limite."
    ),
    "Number of starts allowed within StartLimitIntervalSec=.": (
        "Numero di avvii permessi entro StartLimitIntervalSec=."
    ),
    "Maximum time a start or stop job of this unit may wait in the queue and run.": (
        "Tempo massimo che un job di avvio o arresto di questa unit può attendere in coda "
        "ed eseguire."
    ),
    "Add the usual dependencies on basic system targets. Turn off only for early boot or "
    "late shutdown units.": (
        "Aggiunge le dipendenze abituali dai target di base del sistema. Da disattivare solo "
        "per unit di inizio avvio o di fine spegnimento."
    ),
    "Stop this unit automatically when no other active unit needs it.": (
        "Ferma questa unit automaticamente quando nessun'altra unit attiva ne ha bisogno."
    ),
    "Refuse a start requested directly by the user: only dependencies may start it.": (
        "Rifiuta l'avvio richiesto direttamente dall'utente: solo le dipendenze possono avviarla."
    ),
    "Refuse a stop requested directly by the user.": (
        "Rifiuta l'arresto richiesto direttamente dall'utente."
    ),
    # directive catalogue: [Service]
    "When systemd considers the service started. simple: right after fork; exec: once the "
    "binary runs; forking: when the parent exits; oneshot: when the process exits; dbus: when "
    "BusName= appears on the bus; notify: when it sends READY=1; idle: like simple, after "
    "other jobs finish.": (
        "Quando systemd considera avviato il servizio. simple: subito dopo il fork; exec: "
        "quando il binario è in esecuzione; forking: quando il processo padre termina; oneshot: "
        "quando il processo termina; dbus: quando BusName= compare sul bus; notify: quando "
        "invia READY=1; idle: come simple, dopo la fine degli altri job."
    ),
    "Keep the service active after all its processes exit. Typical with Type=oneshot.": (
        "Mantiene attivo il servizio dopo che tutti i suoi processi sono terminati. Tipico "
        "con Type=oneshot."
    ),
    "Command that starts the service: absolute path, or a command in the default PATH. Only "
    "Type=oneshot accepts more than one. In a drop-in, an empty ExecStart= first clears the "
    "list.": (
        "Comando che avvia il servizio: percorso assoluto, o un comando nel PATH predefinito. "
        "Solo Type=oneshot ne accetta più di uno. In un drop-in, un ExecStart= vuoto svuota "
        "prima la lista."
    ),
    "Commands run before ExecStart=. Prefix with - to ignore their failure.": (
        "Comandi eseguiti prima di ExecStart=. Con il prefisso - il loro fallimento è ignorato."
    ),
    "Commands run after the service has started.": (
        "Comandi eseguiti dopo che il servizio è partito."
    ),
    "Commands run before ExecStartPre=: exit code 1 to 254 skips the start without an error, "
    "255 fails it.": (
        "Comandi eseguiti prima di ExecStartPre=: un codice di uscita da 1 a 254 salta l'avvio "
        "senza errore, 255 lo fa fallire."
    ),
    "Command run by systemctl reload.": "Comando eseguito da systemctl reload.",
    "Command that stops the service. Without it, the processes get KillSignal=.": (
        "Comando che ferma il servizio. Se manca, i processi ricevono KillSignal=."
    ),
    "Commands run after the service stopped, also when it failed.": (
        "Comandi eseguiti dopo l'arresto del servizio, anche quando è fallito."
    ),
    "File where a Type=forking service writes the PID of its main process.": (
        "File in cui un servizio Type=forking scrive il PID del processo principale."
    ),
    "D-Bus name the service acquires. Required with Type=dbus.": (
        "Nome D-Bus acquisito dal servizio. Obbligatorio con Type=dbus."
    ),
    "Which processes may send status notifications (sd_notify) for the service.": (
        "Quali processi possono inviare notifiche di stato (sd_notify) per il servizio."
    ),
    "When to restart the service after its process exits, is killed or times out.": (
        "Quando riavviare il servizio dopo che il processo termina, viene ucciso o va in timeout."
    ),
    "Time to wait before restarting the service.": "Attesa prima di riavviare il servizio.",
    "Extra exit codes and signals that count as a clean exit.": (
        "Codici di uscita e segnali aggiuntivi considerati come uscita regolare."
    ),
    "Exit codes and signals that never trigger a restart.": (
        "Codici di uscita e segnali che non causano mai un riavvio."
    ),
    "Maximum start-up time; past it the service is considered failed. infinity disables the "
    "timeout.": (
        "Tempo massimo di avvio; oltre, il servizio è considerato fallito. infinity disattiva "
        "il timeout."
    ),
    "Maximum time to wait for the stop; past it the processes get SIGKILL.": (
        "Tempo massimo di attesa dell'arresto; oltre, i processi ricevono SIGKILL."
    ),
    "Sets both TimeoutStartSec= and TimeoutStopSec=.": (
        "Imposta sia TimeoutStartSec= sia TimeoutStopSec=."
    ),
    "Maximum running time: past it the service is stopped and counted as failed.": (
        "Tempo massimo di esecuzione: oltre, il servizio viene fermato e considerato fallito."
    ),
    "The service must send WATCHDOG=1 at least this often, or it is considered failed.": (
        "Il servizio deve inviare WATCHDOG=1 almeno con questa frequenza, altrimenti è "
        "considerato fallito."
    ),
    "Which processes are killed on stop: the whole control group, the main process first "
    "and then the rest (mixed), only the main process, or none.": (
        "Quali processi vengono terminati all'arresto: l'intero control group, prima il "
        "processo principale e poi gli altri (mixed), solo il processo principale, o nessuno."
    ),
    "Signal sent to stop the service.": "Segnale inviato per fermare il servizio.",
    "Send SIGKILL to processes still running after TimeoutStopSec=.": (
        "Invia SIGKILL ai processi ancora in esecuzione dopo TimeoutStopSec=."
    ),
    "Working directory of the processes. ~ means the home of User=; a - prefix ignores a "
    "missing directory.": (
        "Directory di lavoro dei processi. ~ indica la home di User=; il prefisso - ignora una "
        "directory mancante."
    ),
    "Run the processes with this directory as root (chroot).": (
        "Esegue i processi con questa directory come radice (chroot)."
    ),
    "User the processes run as (name or UID). System services only: user services already "
    "run as you.": (
        "Utente con cui girano i processi (nome o UID). Solo servizi di sistema: i servizi "
        "utente girano già come te."
    ),
    "Group the processes run as.": "Gruppo con cui girano i processi.",
    "Run as a temporary user and group allocated when the service starts.": (
        "Gira con un utente e un gruppo temporanei, creati all'avvio del servizio."
    ),
    "Extra groups for the processes.": "Gruppi aggiuntivi per i processi.",
    "File mode creation mask of the processes, in octal.": (
        "Maschera dei permessi dei file creati dai processi, in ottale."
    ),
    "Environment variables as KEY=value, separated by spaces. Quote assignments that contain "
    "spaces.": (
        "Variabili d'ambiente come CHIAVE=valore, separate da spazi. Metti tra virgolette le "
        "assegnazioni che contengono spazi."
    ),
    "File with KEY=value lines to read variables from. Prefix with - to ignore a missing file.": (
        "File con righe CHIAVE=valore da cui leggere le variabili. Il prefisso - ignora un file "
        "mancante."
    ),
    "Names of variables passed on from the service manager's own environment.": (
        "Nomi delle variabili da passare dall'ambiente del gestore dei servizi."
    ),
    "Where standard output goes: journal, null, inherit, tty, file:path, append:path, "
    "truncate:path, socket.": (
        "Dove va lo standard output: journal, null, inherit, tty, file:percorso, "
        "append:percorso, truncate:percorso, socket."
    ),
    "Where standard error goes; same values as StandardOutput=.": (
        "Dove va lo standard error; stessi valori di StandardOutput=."
    ),
    "Where standard input comes from: null, tty, tty-force, tty-fail, data, file:path, socket.": (
        "Da dove arriva lo standard input: null, tty, tty-force, tty-fail, data, "
        "file:percorso, socket."
    ),
    "Name used for the messages of the service in the journal.": (
        "Nome usato per i messaggi del servizio nel journal."
    ),
    "Scheduling priority, from -20 (highest) to 19 (lowest).": (
        "Priorità di scheduling, da -20 (massima) a 19 (minima)."
    ),
    "Maximum number of open files: one value, or soft:hard.": (
        "Numero massimo di file aperti: un valore, oppure soft:hard."
    ),
    "Maximum number of processes of the user.": "Numero massimo di processi dell'utente.",
    "Directories created under /run (or $XDG_RUNTIME_DIR for user services) when the service "
    "starts, owned by it and removed when it stops.": (
        "Directory create in /run (o $XDG_RUNTIME_DIR per i servizi utente) all'avvio del "
        "servizio, di sua proprietà e rimosse all'arresto."
    ),
    "Directories created under /var/lib (or ~/.local/state) for persistent data, owned by the "
    "service.": (
        "Directory create in /var/lib (o ~/.local/state) per i dati persistenti, di proprietà "
        "del servizio."
    ),
    "Directories created under /var/cache (or ~/.cache), owned by the service.": (
        "Directory create in /var/cache (o ~/.cache), di proprietà del servizio."
    ),
    "Directories created under /var/log, owned by the service.": (
        "Directory create in /var/log, di proprietà del servizio."
    ),
    "Directories created under /etc (or ~/.config) for the configuration of the service.": (
        "Directory create in /etc (o ~/.config) per la configurazione del servizio."
    ),
    "Mount read-only for the service: /usr and /boot (yes), also /etc (full), or the whole "
    "file system except /dev, /proc and /sys (strict).": (
        "Monta in sola lettura per il servizio: /usr e /boot (yes), anche /etc (full), o "
        "l'intero file system tranne /dev, /proc e /sys (strict)."
    ),
    "Make /home, /root and /run/user inaccessible (yes), read-only, or empty (tmpfs).": (
        "Rende /home, /root e /run/user inaccessibili (yes), in sola lettura (read-only) o "
        "vuote (tmpfs)."
    ),
    "Give the service its own private /tmp and /var/tmp.": (
        "Dà al servizio /tmp e /var/tmp privati."
    ),
    "Give the service a minimal /dev without physical devices.": (
        "Dà al servizio una /dev minima, senza dispositivi fisici."
    ),
    "Run the service in its own network namespace with only a loopback interface.": (
        "Esegue il servizio in un proprio namespace di rete con la sola interfaccia di loopback."
    ),
    "Prevent the processes and their children from gaining privileges, for example "
    "through setuid binaries.": (
        "Impedisce ai processi e ai loro figli di acquisire privilegi, ad esempio tramite "
        "binari setuid."
    ),
    "Make /proc/sys, /sys and similar kernel settings read-only.": (
        "Rende in sola lettura /proc/sys, /sys e altre impostazioni del kernel."
    ),
    "Forbid loading and unloading kernel modules.": (
        "Vieta il caricamento e la rimozione di moduli del kernel."
    ),
    "Paths left writable when ProtectSystem= makes the rest read-only.": (
        "Percorsi lasciati scrivibili quando ProtectSystem= rende il resto in sola lettura."
    ),
    "Paths made read-only for the service.": "Percorsi resi in sola lettura per il servizio.",
    "Paths made completely inaccessible for the service.": (
        "Percorsi resi del tutto inaccessibili per il servizio."
    ),
    "Capabilities the processes may ever hold; prefix with ~ to list the ones to drop.": (
        "Capability che i processi possono avere; con il prefisso ~ si elencano quelle da togliere."
    ),
    "Capabilities granted to the processes even when they run as an unprivileged user.": (
        "Capability concesse ai processi anche quando girano come utente non privilegiato."
    ),
    "Memory throttling limit: above it the processes are slowed down and memory is reclaimed.": (
        "Limite di rallentamento della memoria: oltre, i processi vengono rallentati e la "
        "memoria recuperata."
    ),
    "Hard memory limit: above it the OOM killer acts. Bytes with K/M/G/T suffix, a "
    "percentage of RAM, or infinity.": (
        "Limite rigido di memoria: oltre, interviene l'OOM killer. Byte con suffisso K/M/G/T, "
        "una percentuale della RAM, o infinity."
    ),
    "Maximum CPU time relative to one CPU: 200% means two whole CPUs.": (
        "Tempo CPU massimo rispetto a una CPU: 200% significa due CPU intere."
    ),
    "Relative share of CPU time, from 1 to 10000 (default 100).": (
        "Quota relativa di tempo CPU, da 1 a 10000 (predefinito 100)."
    ),
    "Relative share of disk I/O, from 1 to 10000 (default 100).": (
        "Quota relativa di I/O su disco, da 1 a 10000 (predefinito 100)."
    ),
    "Maximum number of processes and threads, or a percentage of the system limit.": (
        "Numero massimo di processi e thread, o una percentuale del limite di sistema."
    ),
    "How likely the kernel is to kill the processes when memory runs out, from -1000 (never) "
    "to 1000.": (
        "Quanto è probabile che il kernel termini i processi quando la memoria finisce, da "
        "-1000 (mai) a 1000."
    ),
    "Slice (resource group) the service is placed in.": (
        "Slice (gruppo di risorse) in cui viene messo il servizio."
    ),
    # directive catalogue: [Install]
    "When enabled, the unit starts together with the listed target (a symlink in its .wants/ "
    "directory). Usually multi-user.target, or default.target for user units.": (
        "Quando è abilitata, la unit parte insieme al target indicato (un link simbolico nella "
        "sua directory .wants/). Di solito multi-user.target, o default.target per le unit "
        "utente."
    ),
    "Like WantedBy=, but creates a Requires= dependency (.requires/ directory).": (
        "Come WantedBy=, ma crea una dipendenza Requires= (directory .requires/)."
    ),
    "When enabled, the listed units keep this unit running, restarting it if it stops.": (
        "Quando è abilitata, le unit indicate tengono in esecuzione questa unit, riavviandola "
        "se si ferma."
    ),
    "Additional names for the unit, created as symlinks when enabled.": (
        "Nomi aggiuntivi della unit, creati come link simbolici quando viene abilitata."
    ),
    "Other units enabled and disabled together with this one.": (
        "Altre unit abilitate e disabilitate insieme a questa."
    ),
    "For a template unit (name@.service): the instance enabled when none is given.": (
        "Per una unit template (nome@.service): l'istanza abilitata quando non ne viene "
        "indicata nessuna."
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
