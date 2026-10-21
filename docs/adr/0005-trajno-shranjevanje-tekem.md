---
status: sprejeto
date: 2026-10-21
decision-makers: Valeri Kamburov
---

# Trajno shranjevanje prenesenih tekem

## Kontekst in problem

Vsaka analiza potrebuje zadnje tekme nasprotnikov, učni cevovod pa veliko tekem za učenje modelov. Ali naj sistem tekme ob vsaki analizi znova prenese iz Riot API ali naj jih shrani v svojo bazo?

## Dejavniki odločitve

- Omejitev klicev Riot API.
- Končana tekma se nikoli več ne spremeni.
- Model potrebuje zgodovinske podatke za učenje.
- Hitrost ponovnih analiz istih igralcev.

## Obravnavane možnosti

- Trajno shranjevanje tekem v PostgreSQL
- Kratkotrajni predpomnilnik (Redis s časom poteka)
- Brez shranjevanja, vedno prenos iz Riot API

## Odločitev

Izbrana možnost: "Trajno shranjevanje tekem v PostgreSQL", ker so tekme nespremenljive, zato vsako prenesemo le enkrat, hkrati pa nastaja učna množica za model.

### Posledice

- Dobro, ker ponovna analiza istih igralcev prenese samo nove tekme.
- Dobro, ker se iz istih podatkov učita oba modela in računajo agregati (`build_stats`).
- Dobro, ker je podatke mogoče analizirati tudi brez povezave z Riot API.
- Slabo, ker baza hitro raste (10 vrstic `match_participants` na tekmo); surove tekme hranimo 6 mesecev, agregate dlje.
- Slabo, ker hranimo podatke o igralcih, ki niso naši uporabniki; omejeno na javne podatke tekem, z možnostjo skritja profila.

### Potrditev

Pred prenosom tekme delavec preveri, ali `match_id` že obstaja v bazi. Metrika "delež tekem iz baze" pri analizah je spremljana v administraciji.

## Prednosti in slabosti možnosti

### Trajno shranjevanje

- Dobro, ker najbolj zmanjša porabo klicev.
- Dobro, ker gradi učne podatke.
- Slabo, ker zahteva upravljanje rasti baze.

### Kratkotrajni predpomnilnik

- Dobro, ker ne raste neomejeno.
- Slabo, ker po poteku tekme spet prenašamo.
- Slabo, ker ne nastaja učna množica.

### Brez shranjevanja

- Dobro, ker je najpreprostejše.
- Slabo, ker hitro izčrpa omejitev klicev.
- Slabo, ker učenje modela ni mogoče.

## Dodatne informacije

Povezano: ADR-0001, ADR-0006.