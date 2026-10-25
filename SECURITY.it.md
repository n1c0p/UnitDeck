<!--
SPDX-License-Identifier: GPL-3.0-or-later
SPDX-FileCopyrightText: 2026 Nicola Palmieri (n1c0p)
-->

# Politica di sicurezza

[English](SECURITY.md) | **Italiano**

## Versioni supportate

Solo l'ultima release pubblicata nella [pagina Releases](https://github.com/n1c0p/UnitDeck/releases) riceve correzioni.

## Segnalare una vulnerabilità

Non aprire una issue pubblica per un problema di sicurezza. Segnalalo in privato tramite la [segnalazione di vulnerabilità di GitHub](https://github.com/n1c0p/UnitDeck/security/advisories/new) o via e-mail a npalmieri@hotmail.com. Riceverai una risposta entro una settimana; la correzione viene pubblicata come nuova release e accreditata a te, salvo diversa preferenza.

## Cosa conta di più

UnitDeck gira come utente normale e delega ogni azione privilegiata a polkit. Le parti che meritano attenzione sono:

- `helper/unitdeck-helper`, l'unico codice eseguito come root (tramite `pkexec`): deve accettare solo le operazioni documentate sotto `/etc/systemd/system`;
- `packaging/eu.nicop.unitdeck.policy`, la policy polkit che fissa il percorso dell'helper;
- le chiamate D-Bus con autorizzazione interattiva sul bus di sistema;
- il meccanismo di aggiornamento (download, verifica SHA256, `pkexec apt-get`).
