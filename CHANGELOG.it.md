# Changelog

[English](CHANGELOG.md) | **Italiano**

In questo file sono documentate tutte le modifiche rilevanti del progetto.

Il formato segue [Keep a Changelog](https://keepachangelog.com/it-IT/1.1.0/) e il progetto adotta il [Versionamento Semantico](https://semver.org/lang/it/spec/v2.0.0.html).

## [Unreleased]

### Aggiunto

- Tab Servizi di sistema: stesse funzioni della tab utente sul bus di sistema; le azioni privilegiate usano l'autorizzazione interattiva D-Bus, così polkit mostra il dialogo di autenticazione del desktop solo quando serve, e un'autenticazione annullata o rifiutata viene riportata nella barra di stato senza alcun crash.
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

[Unreleased]: https://github.com/n1c0p/UnitDeck/commits/develop
