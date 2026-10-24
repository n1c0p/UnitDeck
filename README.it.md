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

- Una distribuzione Linux con **systemd** e **polkit** (obiettivo principale: versioni recenti di Ubuntu con GNOME, su X11 o Wayland).
- Un agente di autenticazione polkit (incluso in tutti i principali ambienti desktop).

## Installazione

Quando sarà pubblicata la prima release, scarica il pacchetto `.deb` dalla [pagina Releases](https://github.com/n1c0p/UnitDeck/releases) e installalo:

```bash
sudo apt install ./unitdeck_<versione>_amd64.deb
```

### Dai sorgenti

Le istruzioni per eseguire UnitDeck dai sorgenti verranno aggiunte con l'avanzare dello sviluppo. UnitDeck è scritto in **Python 3.12+** con **PyQt6**.

## Contribuire

I contributi sono benvenuti. Il repository usa due branch permanenti:

- `main`: corrisponde sempre all'ultima release;
- `develop`: sviluppo in corso, destinazione di tutte le pull request.

Parti da `develop` creando un branch `feature/*` o `fix/*` e apri una pull request verso `develop`. Maggiori dettagli saranno disponibili in `CONTRIBUTING.md`.

La documentazione è mantenuta in inglese e in italiano: quando modifichi `README.md` o `CHANGELOG.md`, aggiorna anche `README.it.md` e `CHANGELOG.it.md`. Se non ti trovi a tuo agio con una delle due lingue, segnalalo nella pull request e la traduzione verrà completata dal maintainer.

I template dei servizi sono semplici file nel repository: aggiungerne uno nuovo con una pull request è un ottimo primo contributo.

## Changelog

Tutte le modifiche rilevanti sono elencate in [CHANGELOG.it.md](CHANGELOG.it.md).

## Licenza

Copyright (C) 2026 Nicola ([n1c0p](https://github.com/n1c0p))

UnitDeck è software libero: puoi redistribuirlo e/o modificarlo secondo i termini della GNU General Public License, pubblicata dalla Free Software Foundation, nella versione 3 della licenza o (a tua scelta) in una qualsiasi versione successiva.

UnitDeck è distribuito nella speranza che sia utile, ma SENZA ALCUNA GARANZIA, nemmeno la garanzia implicita di COMMERCIABILITÀ o di IDONEITÀ PER UNO SCOPO PARTICOLARE. Per i dettagli consulta la [GNU General Public License](LICENSE). Il testo della licenza in `LICENSE` è quello ufficiale in inglese, l'unico con valore legale.
