---
status: sprejeto
date: 2026-10-21
decision-makers: Valeri Kamburov
---

# Uradni Riot API kot glavni vir podatkov o igralcih in tekmah

## Kontekst in problem

Rift_Help potrebuje aktivne tekme, zgodovino tekem in časovnice igralcev. Podatki so dostopni na več mestih: uradni Riot API, statistične strani (op.gg, u.gg) in neuradne knjižnice. Od kod naj sistem jemlje podatke, da bo zanesljiv, dovoljen in uporaben za učenje modela?

## Dejavniki odločitve

- Pravila Riot za razvijalce priporočajo zajem podatkov prek podprtih storitev Riot.
- Za učenje modela rabimo posamezne tekme z obema ekipama in časovnicami, ne povprečij na šampiona.
- Vir mora biti stabilen; sprememba HTML strani ne sme pokvariti aplikacije.
- OP.GG strganje na splošno dovoli, zahteva pa navedbo vira in zmerno število zahtevkov.

## Obravnavane možnosti

- Uradni Riot API in Data Dragon
- Strganje strani op.gg ali u.gg
- Kombinacija: Riot API za tekme, strganje za statistiko buildov

## Odločitev

Izbrana možnost: "Uradni Riot API in Data Dragon", ker je edini vir, ki daje posamezne tekme z nasprotno sestavo in časovnicami, kar je nujno za učenje modela, hkrati pa je v skladu s pravili Riot.

### Posledice

- Dobro, ker je aplikacija skladna s pravili in jo je kasneje mogoče registrirati za produkcijski ključ.
- Dobro, ker so podatki strukturirani (JSON) in dokumentirani, brez razčlenjevanja HTML.
- Dobro, ker statistiko buildov izračunamo sami in jo lahko prilagodimo nasprotni sestavi.
- Slabo, ker razvojni ključ dovoljuje le 20 klicev na sekundo in 100 klicev na 2 minuti (rešeno v ADR-0004 in ADR-0005).
- Slabo, ker razvojni ključ poteče vsakih 24 ur; za razvoj in teste uporabljamo posnete odgovore (način `fixtures`).

### Potrditev

V kodi Riot API kliče samo en modul (Riot prehod). Pregled kode preveri, da se učni podatki pridobivajo samo prek tega modula.

## Prednosti in slabosti možnosti

### Uradni Riot API in Data Dragon

- Dobro, ker je dovoljen in dokumentiran.
- Dobro, ker vsebuje časovnice tekem (Match-V5 timeline) z vrstnim redom nakupov.
- Slabo, ker ima stroge omejitve klicev.

### Strganje op.gg ali u.gg

- Dobro, ker že ponuja izračunane statistike buildov iz zelo velikega števila tekem.
- Nevtralno, ker OP.GG strganje dovoli ob navedbi vira in brez obremenjevanja strežnika.
- Slabo, ker so to povprečja na šampiona brez nasprotne sestave, zato se model iz njih ne more naučiti glavne naloge.
- Slabo, ker se strgalnik ob vsaki spremembi strani razbije.

### Kombinacija

- Dobro, ker bi hitreje prišli do izhodiščne statistike buildov.
- Slabo, ker doda krhek in dodatno vzdrževan del sistema, ki za MVP ni nujen.

## Dodatne informacije

- Pravila Riot: https://developer.riotgames.com/policies/general
- OP.GG: https://help.op.gg/hc/en-us/articles/31091405109401-Can-I-use-OP-GG-data
- OP.GG je kandidat za pomožni vir izhodiščnih buildov; če bo dodan, ga zapišemo v novem ADR.
- Povezano: ADR-0004 (asinhrona analiza), ADR-0005 (shranjevanje tekem).