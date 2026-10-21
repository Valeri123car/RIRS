---
status: sprejeto
date: 2026-10-21
decision-makers: Valeri Kamburov
---

# Server-Sent Events za prenos napredka analize

## Kontekst in problem

Analiza teče asinhrono v delavcih (ADR-0004) in traja do minute. Frontend mora sproti prikazovati napredek in delne rezultate. Kako naj strežnik obvešča brskalnik?

## Dejavniki odločitve

- Podatki tečejo samo od strežnika k brskalniku.
- Povezava mora preživeti proxy in samodejno ponovno povezati ob prekinitvi.
- Čim manj dodatne infrastrukture in kode.

## Obravnavane možnosti

- Server-Sent Events (SSE)
- WebSocket
- Periodično poizvedovanje (polling)

## Odločitev

Izbrana možnost: "Server-Sent Events", ker je komunikacija enosmerna, SSE pa deluje prek običajnega HTTP in se samodejno ponovno poveže.

### Posledice

- Dobro, ker brskalnik podpira SSE z vgrajenim `EventSource`, brez dodatne knjižnice.
- Dobro, ker deluje prek običajnih HTTP proxyjev in z obstoječo avtentikacijo.
- Dobro, ker so delni rezultati prikazani takoj, ko jih delavec objavi.
- Slabo, ker SSE ne omogoča pošiljanja sporočil od brskalnika k strežniku; če bo to kdaj potrebno, bo treba nov ADR.
- Slabo, ker vsak odprt tok zaseda eno povezavo na strežniku.

### Potrditev

Ob prekinjeni povezavi frontend prebere trenutno stanje z `GET /analyses/{id}`, zato uporabnik ne izgubi rezultatov. To pokriva e2e test s simulirano prekinitvijo.

## Prednosti in slabosti možnosti

### SSE

- Dobro, ker je preprost in enosmeren.
- Slabo, ker ne podpira dvosmerne komunikacije.

### WebSocket

- Dobro, ker je dvosmeren.
- Slabo, ker je kompleksnejši in dvosmernosti ne potrebujemo.

### Polling

- Dobro, ker je najpreprostejši za implementacijo.
- Slabo, ker povzroča zamik in nepotrebne zahtevke.

## Dodatne informacije

Povezano: ADR-0004.