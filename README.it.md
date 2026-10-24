# UnitDeck

[English](README.md) | **Italiano**

[![Licenza: GPL v3+](https://img.shields.io/badge/License-GPLv3%2B-blue.svg)](LICENSE)
[![Ultima release](https://img.shields.io/github/v/release/n1c0p/UnitDeck?include_prereleases&sort=semver)](https://github.com/n1c0p/UnitDeck/releases)

**UnitDeck** è un'applicazione desktop per Linux che permette di gestire i **servizi systemd**, sia **di sistema** sia **utente**, da un'interfaccia grafica semplice e ordinata.

> 🚧 **Stato: sviluppo iniziale.** Non è ancora disponibile nessuna release. Le funzionalità elencate di seguito descrivono gli obiettivi delle prime versioni.

## Perché UnitDeck

Gestire i servizi di solito significa destreggiarsi tra `systemctl`, `systemctl --user`, `journalctl` e un editor aperto con `sudo`. UnitDeck riunisce tutto in un'unica finestra, senza mai eseguire l'interfaccia come root.

## Funzionalità previste

- **Due schede:** servizi di sistema e servizi utente, ciascuna con una tabella ricercabile e filtrabile che mostra stato di caricamento, stato di esecuzione e avvio automatico.
- **Azioni rapide su ogni riga:** avvia, ferma, riavvia, modifica, più ricarica, abilita/disabilita all'avvio, log, maschera/smaschera, ripristina originale ed elimina.
- **Modifica sicura con i drop-in:** per i servizi installati dai pacchetti, le modifiche vengono salvate come drop-in `override.conf` (come fa `systemctl edit`), così sopravvivono agli aggiornamenti. L'azione "Ripristina originale" le annulla. Ogni modifica viene validata con `systemd-analyze verify` prima del salvataggio.
- **Creazione guidata di nuovi servizi:** crea servizi di sistema o utente partendo da template, con validazione e l'opzione "abilita e avvia subito".
- **Log in tempo reale:** l'output del journal per il servizio selezionato, con aggiornamento live e filtro per priorità.
- **Stato sempre aggiornato:** gli aggiornamenti arrivano direttamente da systemd via D-Bus, senza polling.
- **Interruttore per il linger:** permette ai servizi utente di funzionare anche senza login grafico.

## Modello di sicurezza

UnitDeck è progettato per **non girare mai come root** e si rifiuta di partire se viene avviato con privilegi di root.

- I **servizi utente** sono gestiti tramite il bus di sessione: non viene mai chiesta nessuna password.
- I **servizi di sistema** sono gestiti tramite il bus di sistema con l'autorizzazione interattiva di polkit: la finestra di autenticazione nativa del desktop compare **solo** quando esegui un'azione privilegiata (avvio, arresto, modifica, …). Consultare servizi, stato e log non richiede mai la password.
- La **scrittura dei file di sistema** passa da un piccolo helper verificabile, avviato tramite `pkexec`, che accetta solo un insieme fisso di operazioni e solo percorsi sotto `/etc/systemd/system`.
- UnitDeck non legge, non salva e non gestisce mai la tua password: l'autenticazione è interamente delegata a polkit.

## Requisiti

- Una distribuzione Linux con **systemd** e **polkit** (obiettivo principale: versioni recenti di Ubuntu con GNOME, su X11 o Wayland). Il pacchetto `.deb` è compilato su **Ubuntu 24.04 LTS**, la versione più vecchia supportata.
- Un agente di autenticazione polkit (incluso in tutti i principali ambienti desktop).

## Installazione

Quando sarà pubblicata la prima release, scarica il pacchetto `.deb` dalla [pagina Releases](https://github.com/n1c0p/UnitDeck/releases) e installalo:

```bash
sudo apt install ./unitdeck_<versione>_amd64.deb
```

### Dai sorgenti

UnitDeck è scritto in **Python 3.12+** con **PyQt6**.

```bash
git clone https://github.com/n1c0p/UnitDeck.git
cd UnitDeck
python3 -m venv .venv
.venv/bin/pip install -e .
.venv/bin/python -m unitdeck
```

Il numero di versione deriva dai tag git tramite `setuptools-scm`: un checkout tra una release e l'altra riporta una versione di sviluppo.

## Uso

La tab **Servizi utente** elenca tutte le unit `.service` della sessione utente, comprese quelle installate ma non caricate. Ogni riga ha i pulsanti avvia, ferma e riavvia più un menu "⋯" con ricarica, abilita/disabilita all'avvio, maschera/smaschera e log. Le stesse azioni sono disponibili dal menu del tasto destro e, sulla riga selezionata, da tastiera:

| Scorciatoia | Azione |
|-------------|--------|
| `Ctrl+S` | Avvia |
| `Ctrl+T` | Ferma |
| `Ctrl+R` | Riavvia |
| `Ctrl+L` | Mostra log (anche doppio clic) |

La tabella segue i segnali D-Bus di systemd, quindi gli stati si aggiornano da soli. "Ricarica configurazione" esegue un `daemon-reload` dopo che hai modificato i file unit su disco.

L'interfaccia è disponibile in inglese e in italiano: segue la lingua del desktop per impostazione predefinita e il selettore accanto alle tab la cambia in qualsiasi momento.

## Dipendenze e licenze

Tutte le dipendenze sono compatibili con la licenza GPL-3.0-or-later del progetto.

| Pacchetto | Ruolo | Licenza |
|-----------|-------|---------|
| [PyQt6](https://www.riverbankcomputing.com/software/pyqt/) | Toolkit grafico e binding D-Bus (QtDBus) | GPL-3.0-only |
| [setuptools-scm](https://github.com/pypa/setuptools-scm) | Versione dai tag git (solo in fase di build) | MIT |
| [pytest](https://pytest.org/) | Test (solo sviluppo) | MIT |
| [ruff](https://docs.astral.sh/ruff/) | Lint e formattazione (solo sviluppo) | MIT |
| [reuse](https://reuse.software/) | Controllo di conformità delle licenze (solo sviluppo) | Apache-2.0 / GPL-3.0-or-later |

## Contribuire

I contributi sono benvenuti. Il repository usa due branch permanenti:

- `main`: corrisponde sempre all'ultima release;
- `develop`: sviluppo in corso, destinazione di tutte le pull request.

Parti da `develop` creando un branch `feature/*` o `fix/*` e apri una pull request verso `develop`. [CONTRIBUTING.it.md](CONTRIBUTING.it.md) descrive il flusso completo: branch, pull request, intestazioni SPDX, come si prepara una release e quali ruleset GitHub proteggono `main`, `develop` e i tag `v*`.

La documentazione è mantenuta in inglese e in italiano: quando modifichi `README.md` o `CHANGELOG.md`, aggiorna anche `README.it.md` e `CHANGELOG.it.md`. Se non ti trovi a tuo agio con una delle due lingue, segnalalo nella pull request e la traduzione verrà completata dal maintainer.

Le release sono automatiche: una pull request da `develop` a `main` imposta la versione in entrambi i changelog e, al merge, il commit viene taggato, il `.deb` compilato e la GitHub Release pubblicata.

I template dei servizi sono semplici file nel repository: aggiungerne uno nuovo con una pull request è un ottimo primo contributo.

## Changelog

Tutte le modifiche rilevanti sono elencate in [CHANGELOG.it.md](CHANGELOG.it.md).

## Licenza

Copyright (C) 2026 Nicola ([n1c0p](https://github.com/n1c0p))

UnitDeck è software libero: puoi redistribuirlo e/o modificarlo secondo i termini della GNU General Public License, pubblicata dalla Free Software Foundation, nella versione 3 della licenza o (a tua scelta) in una qualsiasi versione successiva.

UnitDeck è distribuito nella speranza che sia utile, ma SENZA ALCUNA GARANZIA, nemmeno la garanzia implicita di COMMERCIABILITÀ o di IDONEITÀ PER UNO SCOPO PARTICOLARE. Per i dettagli consulta la [GNU General Public License](LICENSE). Il testo della licenza in `LICENSE` è quello ufficiale in inglese, l'unico con valore legale.
