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

Durante lo sviluppo non toccare mai i servizi di sistema reali: usa unit **utente** usa e getta chiamate `test-unitdeck-*.service` e rimuovile alla fine.

## Flusso delle pull request

1. Parti da un `develop` aggiornato in un branch `feature/<tema>` o `fix/<tema>`.
2. Usa messaggi di commit [Conventional Commits](https://www.conventionalcommits.org/): `feat:`, `fix:`, `docs:`, `chore:`, `ci:`, `refactor:`, `test:`.
3. Ogni file sorgente (Python, script, workflow, `.policy`, `.desktop`, template) inizia con l'intestazione SPDX:

   ```python
   # SPDX-License-Identifier: GPL-3.0-or-later
   # SPDX-FileCopyrightText: 2026 Nicola (n1c0p)
   ```

   I file che non possono contenere un'intestazione sono elencati in `REUSE.toml`. `reuse lint` deve passare.
4. Aggiungi una voce nella sezione **Unreleased** di `CHANGELOG.md` **e** di `CHANGELOG.it.md` per ogni feature o fix completato.
5. Non committare dati personali o di rete: niente indirizzi IP, nomi utente, hostname o percorsi locali, nemmeno nei test o negli esempi.
6. Apri la PR verso `develop`. Il controllo `ci` (ruff, `reuse lint`, pytest) deve passare. Le PR vengono unite con squash.

## Documentazione bilingue

`README`, `CHANGELOG` e `CONTRIBUTING` esistono in inglese (`*.md`, versione di riferimento) e in italiano (`*.it.md`), ciascuno con il selettore di lingua in cima. Ogni modifica a una lingua va riportata nell'altra **nello stesso commit**. Se non te la senti con l'italiano, dillo nella PR e il maintainer si occuperà della traduzione.

## Versioning

Le versioni seguono il [Semantic Versioning](https://semver.org/). La versione installata deriva **solo** dai tag git `vX.Y.Z` tramite `setuptools-scm`: non scrivere mai un numero di versione a mano nel codice. Le prime release sono `0.x`.

## Preparare una release

1. Apri una PR da `develop` a `main`.
2. In quella PR rinomina la sezione `## [Unreleased]` di **entrambi** `CHANGELOG.md` e `CHANGELOG.it.md` in `## [X.Y.Z] - AAAA-MM-GG`, con lo stesso numero e la stessa data nei due file, e aggiungi sopra una nuova sezione `## [Unreleased]` vuota.
3. Il job `release-check` fallisce se la versione manca o non è valida, se il tag `vX.Y.Z` esiste già, se la versione non è maggiore dell'ultima rilasciata o se il changelog italiano non contiene la stessa versione con la stessa data. Il job `branch-origin` fallisce se la PR non arriva da `develop` o da un branch `hotfix/*`.
4. Unisci con un **merge commit** (non squash). Il workflow `release.yml` tagga il commit di merge, compila il `.deb`, pubblica la GitHub Release con la sezione del changelog come note e apre una PR `main` → `develop` dal titolo `chore: sync main into develop after vX.Y.Z`.
5. Unisci la PR di sincronizzazione in `develop` con un merge commit.

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
