<!--
SPDX-License-Identifier: GPL-3.0-or-later
SPDX-FileCopyrightText: 2026 Nicola Palmieri (n1c0p)
-->

# UnitDeck — Specifiche di progetto

Questo documento è la fonte di riferimento per lo sviluppo di UnitDeck. Leggilo per intero prima di iniziare e rispettane i vincoli. Se qualcosa non è chiaro o ti sembra in conflitto, chiedimi prima di decidere.

## Obiettivo

Realizza un'applicazione desktop per Linux (target: Ubuntu recente, kernel 7.x, desktop GNOME, sia X11 che Wayland) che permetta di gestire i servizi systemd, sia di **sistema** sia **utente**, tramite interfaccia grafica.

## Stato attuale del repository

Repository pubblico: https://github.com/n1c0p/UnitDeck

Sono già presenti, su `main` e `develop`:

- `LICENSE`: testo ufficiale della GPLv3, da NON modificare;
- `README.md` (inglese) e `README.it.md` (italiano);
- `CHANGELOG.md` (inglese) e `CHANGELOG.it.md` (italiano), con la sola sezione "Unreleased";
- `.gitignore`: template Python di GitHub, da cui è già stata rimossa la riga `*.spec`;
- `docs/specifiche.md`: questo documento.

Non ricreare questi file da zero: aggiornali man mano che il progetto avanza. Il branch di default è `develop`.

## Stack

- Python 3.12+ e **PyQt6**.
- Comunicazione con systemd e logind **via D-Bus** (`org.freedesktop.systemd1`, `org.freedesktop.login1`), NON facendo parsing dell'output di `systemctl`. Usa QtDBus (PyQt6.QtDBus) se regge i tipi complessi restituiti da systemd (es. `ListUnits` → `a(ssssssouso)`); altrimenti proponi un'alternativa (es. `dbus-fast` con integrazione nel loop Qt) motivando la scelta.
- Progetto gestito con `pyproject.toml`, avviabile con `python -m unitdeck`, test con `pytest`, lint con `ruff`.

## Nome e identificativi

- Nome del progetto: **UnitDeck**.
- Pacchetto Python `unitdeck`, eseguibile `unitdeck`, pacchetto Debian `unitdeck`.
- Identificativo dell'applicazione e prefisso delle action polkit: `eu.nicop.unitdeck`.

## Licenza e repository pubblico

- Il progetto è rilasciato sotto **GPL-3.0-or-later** (obbligatorio, dato che PyQt6 è GPLv3).
- Il file `LICENSE` nella radice resta com'è (serve a GitHub per riconoscere la licenza).
- Rendi il repository conforme alla specifica **REUSE**: aggiungi `LICENSES/GPL-3.0-or-later.txt` e, per i file in cui un'intestazione non è adatta (`LICENSE`, file Markdown esistenti, immagini, file generati), un file `REUSE.toml` con le annotazioni corrispondenti.
- In ogni file sorgente (Python, script, helper, file `.policy`, `.desktop`, template, workflow) inserisci un'intestazione SPDX:

      # SPDX-License-Identifier: GPL-3.0-or-later
      # SPDX-FileCopyrightText: 2026 Nicola Palmieri (n1c0p)

- In `pyproject.toml` imposta `license = "GPL-3.0-or-later"` e i classifier corrispondenti.
- Verifica che ogni dipendenza abbia una licenza compatibile con la GPLv3 ed elencale nel README con la rispettiva licenza.
- Il repository non deve contenere dati personali o di rete: niente IP, nomi utente, hostname o percorsi della mia macchina, né nel codice né nei test né negli esempi.
- Aggiungi un `CONTRIBUTING.md` (in inglese, con versione italiana `CONTRIBUTING.it.md`) che descriva branch, flusso delle PR, preparazione di una release e regola sulla documentazione bilingue.

## Documentazione bilingue

- README, CHANGELOG e CONTRIBUTING esistono in inglese (`*.md`, versione di riferimento) e in italiano (`*.it.md`), con il selettore di lingua in cima a ogni file.
- Ogni modifica a un file in una lingua va riportata anche nell'altro, nello stesso commit.
- Aggiorna la sezione "Unreleased" di **entrambi** i changelog a ogni feature o fix completato.

## Architettura richiesta

Separa nettamente:

1. **Backend systemd** (nessuna dipendenza dalla GUI): elenco unit, stato, azioni, lettura/scrittura dei file unit. Un'unica interfaccia astratta con due implementazioni: bus di sistema e bus di sessione (utente).
2. **Modello dati Qt**: `QAbstractTableModel` + `QSortFilterProxyModel` per ricerca e filtri.
3. **GUI**: finestra principale, dialog di modifica, wizard di creazione, viewer dei log.
4. **Helper privilegiato** per le sole operazioni di scrittura su file di sistema (vedi "Autenticazione").

## Interfaccia

Finestra principale con **due tab**: "Servizi di sistema" e "Servizi utente". Ogni tab contiene:

- **Barra superiore:** campo di ricerca, filtro per stato (tutti / attivi / inattivi / falliti / creati da me), pulsante "Nuovo servizio", pulsante "Ricarica configurazione" (daemon-reload), pulsante aggiorna.
- **Tabella** con colonne: Nome, Descrizione, Caricamento (load state), Stato (active/sub state, con colore: verde attivo, grigio inattivo, rosso failed), Avvio automatico (enabled/disabled/static/masked), Azioni.
- **Colonna Azioni:** icone compatte per Avvia, Ferma, Riavvia, Modifica, più un menu "⋯" con: Ricarica (reload, solo se la unit lo supporta), Abilita/Disabilita all'avvio, Mostra log, Ripristina originale (solo se esistono drop-in o una copia in /etc), Maschera/Smaschera, Elimina (solo per unit create dall'utente in /etc o ~/.config).
  - Abilita o disabilita le azioni in base allo stato (es. "Avvia" disattivato se già attivo).
  - Per le prestazioni disegna i pulsanti tramite un **delegate**, non con `setIndexWidget` su ogni riga.
  - Ogni icona del delegate deve avere: tooltip con il nome dell'azione, evidenziazione al passaggio del mouse, aspetto disattivato quando l'azione non è disponibile.
  - Le stesse azioni devono essere raggiungibili anche senza mouse: menu contestuale con il tasto destro sulla riga e scorciatoie da tastiera sulla riga selezionata (es. Ctrl+S avvia, Ctrl+T ferma, Ctrl+R riavvia, Ctrl+E modifica, Ctrl+L log).
  - Doppio clic sulla riga: apre i log del servizio.
- Mostra solo le unit `.service`, includendo anche i servizi installati ma non caricati (combina `ListUnits` e `ListUnitFiles`).
- Aggiornamento automatico dello stato tramite i segnali D-Bus (`PropertiesChanged`, `UnitNew`/`UnitRemoved`, `Subscribe` sul Manager), non tramite polling.
- Nella tab utente: indicatore e interruttore per il **linger** dell'utente corrente (metodo `SetUserLinger` di logind via D-Bus, con autorizzazione interattiva).
- Barra di stato con l'esito dell'ultima operazione; errori mostrati in modo leggibile, con il messaggio originale di systemd consultabile.
- Tutte le chiamate D-Bus devono essere **asincrone**: la GUI non deve mai bloccarsi (i servizi `oneshot` impiegano anche diversi secondi per completare lo start) e deve mostrare un indicatore di attività sulla riga interessata.

## Autenticazione (requisito critico)

- La GUI gira **sempre come utente normale**. All'avvio controlla di NON essere eseguita come root (`os.geteuid() == 0`): in quel caso mostra un messaggio di errore e termina, senza alcuna opzione per aggirare il controllo. Non usare mai sudo/pkexec sull'intera applicazione.
- La password viene richiesta SOLO al momento dell'operazione privilegiata: azioni sui servizi di sistema, creazione/modifica/eliminazione di file di sistema, linger. Mai all'avvio, mai alla semplice visualizzazione: elenco, stato e log dei servizi di sistema devono essere leggibili senza autenticazione.
- Azioni sui servizi di sistema (start/stop/restart/reload/enable/disable/mask): chiamate D-Bus sul **bus di sistema** con il flag di *interactive authorization* attivo, così systemd delega a **polkit**, che mostra la finestra di autenticazione nativa del desktop. Gestisci il caso di autenticazione annullata o negata senza crash.
- Servizi utente: bus di sessione, nessuna autenticazione.
- Scrittura di file di sistema: tramite un **helper** minimale lanciato con `pkexec` e una **policy polkit** dedicata (action id con prefisso `eu.nicop.unitdeck`). L'helper accetta solo operazioni ben definite: scrivi drop-in, rimuovi drop-in, scrivi unit in /etc/systemd/system, elimina unit creata dall'utente, daemon-reload. Deve validare rigorosamente i percorsi (solo sotto /etc/systemd/system, nomi unit validi, niente path traversal) e non eseguire mai comandi arbitrari.
- Nella policy dell'helper usa `auth_admin_keep`, così polkit ricorda l'autenticazione per qualche minuto e salvataggio + daemon-reload non chiedono la password due volte. Documenta nel README come passare ad `auth_admin` per chi preferisce che la password venga chiesta ogni volta.
- Nessuna password viene mai letta, salvata o gestita dall'applicazione: tutta l'autenticazione passa dalla finestra nativa di polkit.

## Modifica di un servizio (dialog modale)

- Editor di testo con evidenziazione sintattica per il formato INI di systemd e numeri di riga.
- Pannello in sola lettura con la **configurazione effettiva** (file principale + tutti i drop-in, come `systemctl cat`), con l'indicazione del percorso di ogni file.
- Comportamento in base a dove si trova la unit:
  - **Unit fornita da un pacchetto** (`/usr/lib/systemd/...`): per impostazione predefinita l'editor crea o modifica un **drop-in** `override.conf` in `/etc/systemd/system/<unit>.d/` (o `~/.config/systemd/user/<unit>.d/` per i servizi utente). L'editor parte vuoto o con il drop-in esistente, con un commento che spiega che basta scrivere solo le direttive da cambiare (ricordando che per sostituire liste come `ExecStart=` va prima inserita una riga `ExecStart=` vuota). Un'opzione secondaria, con avviso, permette di creare invece una copia completa del file.
  - **Unit creata dall'utente** (già in `/etc/systemd/system/` o `~/.config/systemd/user/`): modifica diretta del file, nessun drop-in.
- Azione "Ripristina originale": rimuove drop-in e copie in /etc o ~/.config per le unit fornite da pacchetto (equivalente a `systemctl revert`), con conferma.
- Prima di salvare: validazione con `systemd-analyze verify` (con `--user` per i servizi utente) e visualizzazione degli avvisi. Backup del file precedente.
- Dopo il salvataggio: daemon-reload automatico e proposta di riavviare il servizio se è attivo.

## Nuovo servizio

Pulsante "Nuovo servizio" in entrambe le tab. Apre un wizard che crea la unit nel percorso corretto in base alla tab da cui è stato aperto:

- tab utente → `~/.config/systemd/user/`, nessuna autenticazione;
- tab di sistema → `/etc/systemd/system/` tramite l'helper privilegiato (richiesta password via polkit al salvataggio).

Passi del wizard:

1. **Nome e template.** Nome del servizio validato secondo le regole di systemd. Se esiste già una unit con lo stesso nome in qualunque percorso di ricerca di systemd, mostra un errore e non sovrascrivere mai. Il template si sceglie tra quelli disponibili per quello scope.
2. **Campi guidati.** Description, Type, ExecStart, ExecStop, Restart, dipendenze (After/Wants), più gli eventuali segnaposto del template. Solo per i servizi di sistema, aggiungi i campi opzionali `User=` e `Group=` con l'avviso che senza di essi il servizio gira come root. Il campo `WantedBy` va precompilato in base allo scope: `default.target` per gli utente, `multi-user.target` per quelli di sistema.
3. **Anteprima.** Editor con il file generato, modificabile a mano, validato con `systemd-analyze verify` (con `--user` per i servizi utente).
4. **Opzioni finali.** Checkbox "Abilita all'avvio" e "Avvia subito" (equivalenti a `enable --now`). Dopo il salvataggio esegui daemon-reload e seleziona il nuovo servizio nella tabella.

Template disponibili:

- Entrambi gli scope: "vuoto", "oneshot con RemainAfterExit", "servizio long-running con Restart=on-failure".
- Solo scope utente: "mount SMB con gio", con segnaposto compilabili nel wizard (server, share, utente, file credenziali). Non va offerto nella tab di sistema, perché `gio` richiede una sessione utente con D-Bus e da servizio di sistema fallisce con "il volume non implementa l'azione mount":

      [Unit]
      Description=Mount SMB share
      After=network-online.target

      [Service]
      Type=oneshot
      RemainAfterExit=yes
      ExecStart=/bin/sh -c '/usr/bin/gio mount "smb://{UTENTE}@{SERVER}/{SHARE}" < %h/{FILE_CREDENZIALI}'
      ExecStop=/usr/bin/gio mount -u "smb://{UTENTE}@{SERVER}/{SHARE}"

      [Install]
      WantedBy=default.target

I template sono file separati in una cartella del progetto, così chiunque possa aggiungerne di nuovi con una pull request.

## Log

Finestra con l'output del journal per la unit selezionata (ultime N righe e modalità "follow" live), con filtro per priorità. Puoi usare `journalctl -u <unit> [--user] -o json`, letto in modo asincrono con `QProcess`.

## Branch, versioning e rilascio

- Branch: `main` = ultima release, `develop` = sviluppo. Le feature partono da develop (`feature/*`, `fix/*`) e rientrano con PR squash. I rilasci passano da PR develop → main con merge commit. I fix urgenti partono da main come `hotfix/*` e vanno riportati anche su develop.
- Versioning semantico. La versione installata si ricava SOLO dai tag git `vX.Y.Z` tramite `setuptools-scm`; nessun numero di versione scritto a mano nei file di codice.
- La versione di ogni release si decide nei changelog: nella PR develop → main, la sezione "Unreleased" di `CHANGELOG.md` e `CHANGELOG.it.md` diventa `## [X.Y.Z] - AAAA-MM-GG`, con lo stesso numero e la stessa data in entrambi i file. La prima release sarà una `0.x`.
- Il rilascio è **automatico** al merge su main (vedi "CI/CD").

## Pacchetto .deb

- Build con **PyInstaller in modalità `--onedir`**, con un file `.spec` versionato nel repo.
- Impacchettamento con `dpkg-deb`, controllo finale con `lintian` (correggi errori e avvisi rilevanti).
- Layout di installazione:
  - applicazione in `/opt/unitdeck/`, con link `/usr/bin/unitdeck`;
  - `.desktop` in `/usr/share/applications/`, icona in `/usr/share/icons/hicolor/`;
  - policy polkit in `/usr/share/polkit-1/actions/eu.nicop.unitdeck.policy`;
  - helper privilegiato in `/usr/libexec/unitdeck/unitdeck-helper`.
- L'helper NON viene compilato con PyInstaller: è uno script Python che usa solo la libreria standard, con shebang `/usr/bin/python3`, così resta piccolo e verificabile. La policy polkit deve puntare al suo percorso fisso tramite `org.freedesktop.policykit.exec.path`.
- Dipendenze del pacchetto: indica in `Depends` solo quelle davvero necessarie (python3 per l'helper, pkexec, eventuali librerie di sistema richieste da Qt come `libxcb-cursor0`), verificandole con un'installazione pulita.
- Script `postinst`/`postrm` minimi (aggiornamento cache icone e desktop database).
- Il .deb va compilato sulla versione di Ubuntu più vecchia supportata (indicala nel README), per la compatibilità con glibc.

## CI/CD con GitHub Actions (completamente automatica)

Usa solo runner standard GitHub-hosted (`ubuntu-*`), mai runner "larger". Il repository è pubblico, quindi l'uso dei runner standard è gratuito.

- **`ci.yml`**, automatico su `pull_request` verso `develop` e `main` e su `push` verso `develop`:
  - job `ci`: lint (ruff), controllo REUSE/SPDX (`reuse lint`), test (pytest);
  - job `branch-origin` (solo PR verso `main`): fallisce se il branch di partenza non è `develop` o `hotfix/*`;
  - job `release-check` (solo PR verso `main`): fallisce se `CHANGELOG.md` non contiene una versione `X.Y.Z` valida, se il tag `vX.Y.Z` esiste già, se la versione non è maggiore dell'ultima rilasciata, o se `CHANGELOG.it.md` non contiene la stessa versione con la stessa data;
  - job `build-preview` (solo push su `develop`): build PyInstaller e .deb, caricato come artifact con conservazione di 14 giorni. Nessuna release, nessun tag;
  - ignora le modifiche solo a documentazione (`paths-ignore`, tranne per `release-check`) e usa `concurrency` per annullare le esecuzioni superate.
- **`release.yml`**, automatico su `push` verso `main` (cioè al merge della PR):
  - legge la versione da `CHANGELOG.md`; se il tag `vX.Y.Z` esiste già, termina senza errori (workflow idempotente, rilanciabile in sicurezza);
  - esegue i test, crea il tag `vX.Y.Z` sul commit di merge, compila con PyInstaller, crea il .deb, esegue `lintian`;
  - pubblica la GitHub Release con il .deb allegato, il checksum SHA256 e come note la sezione di `CHANGELOG.md` (inglese) di quella versione;
  - infine apre automaticamente una PR `main` → `develop` per riallineare i branch (titolo "chore: sync main into develop after vX.Y.Z"), da unire con merge commit;
  - prevedi anche `workflow_dispatch` come trigger di riserva, per rilanciare manualmente una release fallita.
- Tutto avviene in un unico workflow per la release: tag e release creati con il `GITHUB_TOKEN` non attivano altri workflow.
- Permessi del `GITHUB_TOKEN` ridotti al minimo per ogni job (`contents: read` per la CI; `contents: write` e `pull-requests: write` solo per la release). Le action di terze parti vanno fissate a una versione precisa.
- Documenta nel README e in CONTRIBUTING come si prepara una release e quali ruleset impostare su GitHub:
  - `main`: blocco cancellazione e force push, PR obbligatoria (0 approvazioni), controlli obbligatori `ci`, `branch-origin`, `release-check`, nessun vincolo di storia lineare;
  - `develop`: blocco cancellazione e force push, PR obbligatoria (0 approvazioni), controllo obbligatorio `ci`;
  - tag `v*`: blocco di modifica e cancellazione (non della creazione).

## Modo di lavorare

1. Prima di scrivere codice, presentami un **piano**: struttura delle cartelle, scelta della libreria D-Bus con motivazione, e i rischi principali.
2. Fai uno **spike** iniziale che dimostri due cose: elenco delle unit dal bus di sistema e un `StartUnit` di sistema che fa comparire il dialog polkit. Fermati e fammi verificare prima di proseguire.
3. Poi procedi per fasi, chiedendomi conferma tra una e l'altra:
   - **Fase 0:** struttura del progetto, `pyproject.toml`, conformità REUSE, CONTRIBUTING bilingue, workflow `ci.yml` (così posso attivare i ruleset su GitHub dopo la prima esecuzione).
   - **Fase 1 (MVP):** tab utente completa (elenco, avvia/ferma/riavvia, abilita/disabilita, log).
   - **Fase 2:** tab di sistema con polkit.
   - **Fase 3:** editor con drop-in e helper privilegiato.
   - **Fase 4:** nuovo servizio, template, linger, rifiniture.
   - **Fase 5:** pacchetto .deb e workflow `release.yml`.
4. Lavora su branch `feature/*` creati da `develop`, con commit nel formato conventional commits (`feat:`, `fix:`, `docs:`, `chore:`…). Apri una PR verso `develop` per ogni fase.
5. Durante lo sviluppo e i test **non toccare i servizi di sistema reali**: per le prove usa unit utente di test create apposta (es. `test-unitdeck-*.service`) e rimuovile alla fine.
6. Test automatici per il backend con D-Bus simulato (mock), più test di validazione dei percorsi nell'helper.
7. A ogni fase aggiorna README, CHANGELOG (sezione "Unreleased") e CONTRIBUTING in entrambe le lingue. Prima di ogni commit verifica che `reuse lint` passi.

## Fuori scope per ora

Timer, socket e altre unit non-service; gestione di macchine remote; container.
