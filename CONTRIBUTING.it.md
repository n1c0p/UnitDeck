# Contribuire a UnitDeck

[English](CONTRIBUTING.md) | **Italiano**

Grazie per aver pensato di contribuire. Questo documento descrive come è organizzato il repository e come entrano le modifiche.

## Branch

| Branch | Scopo |
|--------|-------|
| `main` | Corrisponde sempre all'ultima release. Vi arrivano solo le PR di rilascio da `develop` e i branch `hotfix/*`. |
| `develop` | Sviluppo in corso, branch di default, destinazione di tutte le PR di feature e fix. |
| `feature/*`, `fix/*` | Creati da `develop`, rientrano in `develop` con merge **squash**. |
| `hotfix/*` | Fix urgenti creati da `main`, uniti in `main` con merge commit e poi riportati su `develop`. |

## Ambiente di sviluppo

```bash
git clone https://github.com/n1c0p/UnitDeck.git
cd UnitDeck
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/python -m unitdeck
```

Prima di ogni commit esegui gli stessi controlli della CI:

```bash
.venv/bin/ruff check . && .venv/bin/ruff format --check .
.venv/bin/reuse lint
.venv/bin/pytest
```

La scrittura dei file unit di **sistema** passa dall'helper privilegiato, che pkexec esegue solo dal suo percorso di installazione. Per provarlo da un checkout, installa una volta l'helper e la sua policy polkit (e rimuovili con `uninstall`):

```bash
packaging/install-dev-helper.sh
```

Durante lo sviluppo non toccare mai i servizi di sistema reali: usa unit **utente** usa e getta chiamate `test-unitdeck-*.service` e rimuovile alla fine.

## Flusso delle pull request

1. Parti da un `develop` aggiornato in un branch `feature/<tema>` o `fix/<tema>`.
2. Usa messaggi di commit [Conventional Commits](https://www.conventionalcommits.org/): `feat:`, `fix:`, `docs:`, `chore:`, `ci:`, `refactor:`, `test:`.
3. Ogni file sorgente (Python, script, workflow, `.policy`, `.desktop`, template) inizia con l'intestazione SPDX:

   ```python
   # SPDX-License-Identifier: GPL-3.0-or-later
   # SPDX-FileCopyrightText: 2026 Nicola Palmieri (n1c0p)
   ```

   I file che non possono contenere un'intestazione sono elencati in `REUSE.toml`. `reuse lint` deve passare.
4. Aggiungi una voce nella sezione **Unreleased** di `CHANGELOG.md` **e** di `CHANGELOG.it.md` per ogni feature o fix completato.
5. Non committare dati personali o di rete: niente indirizzi IP, nomi utente, hostname o percorsi locali, nemmeno nei test o negli esempi.
6. Apri la PR verso `develop`. Il controllo `ci` (ruff, `reuse lint`, pytest) deve passare su ogni PR, anche quelle di sola documentazione: un controllo obbligatorio che non riporta nulla bloccherebbe il merge. Le PR vengono unite con squash.

## Architettura in un paragrafo

`unitdeck.backend` è Python puro: `base.py` (unit, regole delle azioni, l'osservatore `Signal` e i protocolli `Runtime`/`Transport`), `systemd.py` (la logica D-Bus), `unitfiles.py`, `journal.py`, `linger.py`. Un *runtime* fornisce bus, timer e sottoprocessi: `qt_runtime.py` per l'applicazione desktop (QtDBus, QTimer, QProcess) e `asyncio_runtime.py` per l'interfaccia da terminale (dbus-fast, asyncio). Il codice legato a un toolkit sta solo in `unitdeck.gui` (Qt) e, in arrivo con la #38, nel pacchetto del terminale. I test pilotano il backend con il transport e il runtime finti di `tests/fake_transport.py`.

## Aggiungere un template di servizio

I template stanno in `src/unitdeck/templates/` come file `NN-nome.service` (il numero decide l'ordine nel wizard). Ognuno inizia con l'intestazione SPDX e una riga `# unitdeck: name=<etichetta mostrata nel wizard>; scope=user|system|both`. Il corpo è un normale file unit in cui i `{SEGNAPOSTO}` diventano campi del wizard: quelli standard (`DESCRIPTION`, `TYPE`, `EXEC_START`, `EXEC_STOP`, `RESTART`, `AFTER`, `WANTS`, `USER`, `GROUP`, `WANTED_BY`) hanno widget e valori predefiniti dedicati, qualunque altro nome diventa un campo di testo (aggiungi la sua etichetta a `LABELS` in `new_service_wizard.py` e al catalogo italiano). Una riga `Chiave={SEGNAPOSTO}` viene eliminata se il valore resta vuoto. Le altre righe di commento restano nella unit generata: usale per spiegare cosa deve preparare l'utente.

## Documentazione bilingue

`README`, `CHANGELOG` e `CONTRIBUTING` esistono in inglese (`*.md`, versione di riferimento) e in italiano (`*.it.md`), ciascuno con il selettore di lingua in cima. Ogni modifica a una lingua va riportata nell'altra **nello stesso commit**. Le stringhe dell'interfaccia sono scritte in inglese nel codice, avvolte in `tr()`, e tradotte nel catalogo italiano in `src/unitdeck/i18n.py`; un test fallisce se una stringa manca dal catalogo. Se non te la senti con l'italiano, dillo nella PR e il maintainer si occuperà della traduzione.

## Versioning

Le versioni seguono il [Semantic Versioning](https://semver.org/). La versione installata deriva **solo** dai tag git `vX.Y.Z` tramite `setuptools-scm`: non scrivere mai un numero di versione a mano nel codice. Le prime release sono `0.x`.

## Preparare una release

1. Apri una PR da `develop` a `main`.
2. In quella PR rinomina la sezione `## [Unreleased]` di **entrambi** `CHANGELOG.md` e `CHANGELOG.it.md` in `## [X.Y.Z] - AAAA-MM-GG`, con lo stesso numero e la stessa data nei due file, e aggiungi sopra una nuova sezione `## [Unreleased]` vuota.
3. Il job `release-check` fallisce se la versione manca o non è valida, se il tag `vX.Y.Z` esiste già, se la versione non è maggiore dell'ultima rilasciata o se il changelog italiano non contiene la stessa versione con la stessa data. Il job `branch-origin` fallisce se la PR non arriva da `develop` o da un branch `hotfix/*`.
4. Unisci con un **merge commit** (non squash). Il workflow `release.yml` tagga il commit di merge, compila il `.deb`, pubblica la GitHub Release con la sezione del changelog come note e, quando `main` contiene modifiche che mancano a `develop` (hotfix), apre una PR `main` → `develop` dal titolo `chore: sync main into develop after vX.Y.Z`. Dopo una release ordinaria a `develop` manca solo il commit di merge, cosa innocua, e nessuna PR viene aperta: una PR senza differenze non potrebbe mai superare il controllo obbligatorio `ci`.
5. Unisci la PR di sincronizzazione, quando c'è, in `develop` con un merge commit. Le pull request aperte da `GITHUB_TOKEN` non avviano i workflow: se il controllo `ci` non parte, chiudi e riapri la PR.

Gli asset della release sono `unitdeck_X.Y.Z_amd64.deb`, `unitdeck-X.Y.Z-1.x86_64.rpm` e i rispettivi file `.sha256`; il controllo aggiornamenti nell'app si basa su questi nomi e sceglie il formato da `/etc/os-release`. Il pacchetto viene compilato su runner `ubuntu-24.04` (vedi "Compilare il pacchetto" nel README); ogni push su `develop` compila un artifact di anteprima conservato 14 giorni.

Se il workflow di release fallisce, correggi la causa e rilancialo a mano dalla scheda Actions (`workflow_dispatch`): è idempotente e termina senza errori se il tag esiste già.

### Hotfix

Crea `hotfix/<tema>` da `main`, apri una PR verso `main` seguendo i passi di rilascio qui sopra (il changelog riceve una nuova versione patch), poi apri una seconda PR per riportare il fix su `develop`.

## Ruleset su GitHub

Il repository si basa su questi ruleset (Settings → Rules → Rulesets). I controlli obbligatori si possono selezionare solo dopo che il workflow è stato eseguito almeno una volta.

| Destinazione | Regole |
|--------------|--------|
| Branch `main` | Blocco cancellazione; blocco force push; PR obbligatoria (0 approvazioni); controlli obbligatori `ci`, `branch-origin`, `release-check`; **nessun** vincolo di storia lineare. |
| Branch `develop` | Blocco cancellazione; blocco force push; PR obbligatoria (0 approvazioni); controllo obbligatorio `ci`. |
| Tag `v*` | Blocco modifica e cancellazione (la creazione resta permessa, è il workflow di release a crearli). |
