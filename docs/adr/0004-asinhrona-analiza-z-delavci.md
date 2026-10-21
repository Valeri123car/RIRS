---
status: sprejeto
date: 2026-10-21
decision-makers: Valeri Kamburov
---

# Asinhrona analiza tekme z vrsto nalog in delavci

## Kontekst in problem

Analiza aktivne tekme pri prazni bazi potrebuje približno 70 klicev Riot API, razvojni ključ pa dovoljuje 100 klicev na 2 minuti. Analiza zato lahko traja tudi minuto, kar je predolgo za en HTTP zahtevek. Kako izvesti analizo, da uporabnik ne čaka na prazen zaslon in da strežnik ne obtiči?

## Dejavniki odločitve

- Omejitev klicev Riot API (20/s, 100/2 min).
- Uporabnik analizo potrebuje med nalaganjem tekme, zato želi delne rezultate čim prej.
- HTTP zahtevki, dolgi več kot minuto, se pogosto prekinejo (proxy, brskalnik).
- Nočno zbiranje tekem in učenje modelov sta prav tako dolgotrajni nalogi.

## Obravnavane možnosti

- Vrsta nalog (Redis) in delavci (Celery)
- Sinhrona analiza v API zahtevku
- Ozadna opravila znotraj API procesa (FastAPI BackgroundTasks)

## Odločitev

Izbrana možnost: "Vrsta nalog (Redis) in delavci (Celery)", ker loči odziv API od dolgega dela, omogoča prioritetni zajem z delnimi rezultati in hkrati pokrije nočne naloge učnega cevovoda.

### Posledice

- Dobro, ker API takoj vrne `202` z ID analize in ostane odziven.
- Dobro, ker delavec najprej obdela linijskega nasprotnika in junglerja ter sproti objavlja rezultate.
- Dobro, ker se delavce lahko skalira neodvisno od API.
- Dobro, ker isti mehanizem (Celery beat) poganja nočni učni cevovod.
- Slabo, ker sistem dobi dve dodatni komponenti (Redis, delavci), ki ju je treba zagnati in nadzorovati.
- Slabo, ker je razhroščevanje asinhronega toka zahtevnejše od sinhronega klica.

### Potrditev

Integracijski test v načinu `fixtures` preveri, da `POST /analyses` vrne `202` v manj kot 500 ms in da analiza preide skozi stanja `queued → ingesting → profiling → recommending → completed`.

## Prednosti in slabosti možnosti

### Redis + Celery

- Dobro, ker je preverjen in podpira ponovne poskuse ter časovne naloge.
- Slabo, ker zahteva dodatno infrastrukturo.

### Sinhrona analiza

- Dobro, ker je najpreprostejša.
- Slabo, ker zahtevek traja do minute in se lahko prekine.
- Slabo, ker en uporabnik zasede API proces.

### BackgroundTasks v API

- Dobro, ker ne potrebuje dodatnih komponent.
- Slabo, ker se naloge izgubijo ob ponovnem zagonu API.
- Slabo, ker ne podpira časovnih nalog in skaliranja.

## Dodatne informacije

Povezano: ADR-0001 (omejitve Riot API), ADR-0008 (prenos napredka prek SSE).