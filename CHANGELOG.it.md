# Changelog

[English](CHANGELOG.md) | **Italiano**

In questo file sono documentate tutte le modifiche rilevanti del progetto.

Il formato segue [Keep a Changelog](https://keepachangelog.com/it-IT/1.1.0/) e il progetto adotta il [Versionamento Semantico](https://semver.org/lang/it/spec/v2.0.0.html).

## [Unreleased]

### Corretto

- Il download dell'aggiornamento faceva andare in crash l'applicazione appena avviato (segnale di avanzamento incompatibile); gli errori non gestiti ora mostrano una finestra invece di terminare UnitDeck.

## [0.1.1] - 2026-10-25

### Corretto

- Template mount SMB: l'avvio è idempotente se la condivisione è già montata, l'arresto smonta la posizione realmente registrata da gvfs e non lascia più la unit in stato failed.

### Aggiunto

- Codice di condotta (Contributor Covenant 2.1), politica di sicurezza, template per issue e pull request.

### Modificato

- La CI gira su ogni pull request, comprese quelle di sola documentazione o senza differenze, così il controllo obbligatorio `ci` riporta sempre.

## [0.1.0] - 2026-10-24

### Aggiunto

- Pacchetto Debian: bundle PyInstaller onedir in `/opt/unitdeck` con `/usr/bin/unitdeck`, helper in `/usr/libexec/unitdeck`, policy polkit, file desktop, icona e pagina man; compilato da `packaging/build-deb.sh`, controllato con `lintian` e con un test di installazione pulita. `unitdeck --version` e `unitdeck --check`.
- CI: pacchetto di anteprima a ogni push su `develop` (artifact, 14 giorni); `release.yml` tagga il merge su `main`, compila il pacchetto, pubblica la GitHub Release con il checksum SHA256 e la sezione del changelog come note, e apre la PR di sincronizzazione `main` → `develop`.
- Wizard Nuovo servizio: nome e template, campi guidati (con `User=`/`Group=` e avviso root per i servizi di sistema, `WantedBy` precompilato per scope), anteprima modificabile controllata con `systemd-analyze verify`, opzioni abilita/avvia; la nuova unit viene selezionata nella tabella. I template sono file in `src/unitdeck/templates/`: vuoto, oneshot, long-running, mount SMB con gio (solo utente).
- Interruttore Linger nella tab utente, tramite `SetUserLinger` di logind con autorizzazione interattiva.
- Elimina ora ferma e disabilita la unit prima di rimuoverne i file; i colori dell'editor si adattano ai temi scuri; dimensione e posizione della finestra vengono ricordate.
- Editor dei servizi: editor con evidenziazione sintattica e numeri di riga accanto alla configurazione effettiva; drop-in `override.conf` per le unit di pacchetto (copia completa come opzione), modifica diretta per le unit create dall'utente; `systemd-analyze verify` prima del salvataggio, backup `.bak`, `daemon-reload` automatico e proposta di riavvio. "Ripristina originale" (`RevertUnitFiles`) ed "Elimina" per le unit create dall'utente.
- Helper privilegiato `unitdeck-helper` (solo libreria standard) con la sua policy polkit `eu.nicop.unitdeck.manage-unit-files` (`auth_admin_keep`): scrive drop-in e unit solo sotto `/etc/systemd/system`, con validazione rigorosa di nomi e percorsi.
- Tab Servizi di sistema: stesse funzioni della tab utente sul bus di sistema; le azioni privilegiate usano l'autorizzazione interattiva D-Bus, così polkit mostra il dialogo di autenticazione del desktop solo quando serve, e un'autenticazione annullata o rifiutata viene riportata nella barra di stato senza alcun crash.
- Azione "Azzera lo stato fallito" e, quando un job fallisce, il risultato di systemd (es. `start-limit-hit`) nel messaggio di errore.
- Tab Servizi utente: tabella ricercabile e filtrabile delle unit `.service` della sessione (comprese quelle installate ma non caricate), avvia/ferma/riavvia/ricarica, abilita/disabilita all'avvio, maschera/smaschera, visualizzatore del journal con follow live e filtro per priorità, aggiornamento live dai segnali D-Bus di systemd, menu contestuale e scorciatoie da tastiera.
- Interfaccia in inglese e in italiano: segue la lingua del desktop, selezionabile dal menu Impostazioni.
- Barra dei menu con Impostazioni e Informazioni, finestre Informazioni su, e meccanismo di aggiornamento: controllo sulle GitHub Releases (all'avvio, disattivabile, e su richiesta), download del `.deb` con verifica SHA256, installazione tramite `pkexec apt-get`.
- Scheletro del progetto: `pyproject.toml` con versione da `setuptools-scm`, pacchetto `unitdeck` avviabile con `python -m unitdeck`, che rifiuta di partire come root.
- Conformità REUSE: `LICENSES/`, `REUSE.toml` e intestazioni SPDX in ogni file sorgente.
- `CONTRIBUTING.md` e `CONTRIBUTING.it.md` con modello dei branch, processo di rilascio e ruleset GitHub.
- Workflow GitHub Actions: `ci` (ruff, `reuse lint`, pytest) e i controlli `branch-origin` e `release-check` per le pull request verso `main`.
- README del progetto, in inglese e in italiano.
- Licenza GPL-3.0-or-later.
- Questo changelog, in inglese e in italiano.

[Unreleased]: https://github.com/n1c0p/UnitDeck/compare/v0.1.1...develop
[0.1.1]: https://github.com/n1c0p/UnitDeck/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/n1c0p/UnitDeck/releases/tag/v0.1.0
