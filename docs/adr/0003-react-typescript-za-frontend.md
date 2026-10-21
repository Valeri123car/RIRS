---
status: sprejeto
date: 2026-10-21
decision-makers: Valeri Kamburov
---

# React s TypeScriptom (TSX) in Next.js za frontend

## Kontekst in problem

Frontend prikazuje kompleksne podatke analize (variante buildov, časovnico moči, profile igralcev), ki prihajajo postopoma prek SSE. Katero tehnologijo izbrati, da bo prikaz zanesljiv in da napake v podatkih odkrijemo že pri razvoju?

## Dejavniki odločitve

- Odgovori API so obsežni in gnezdeni; napačno ime polja ne sme priti do produkcije.
- Razvijalec React in TypeScript že pozna.
- Javne strani profilov igralcev naj bodo hitre ob prvem nalaganju.
- Na voljo morajo biti knjižnice za grafe in komponente.

## Obravnavane možnosti

- React s TypeScriptom (Next.js)
- React z JavaScriptom (JSX)
- Vue ali Angular

## Odločitev

Izbrana možnost: "React s TypeScriptom (Next.js)", ker tipi, generirani iz OpenAPI specifikacije backenda, ob vsaki spremembi API takoj pokažejo napake v frontendu, razvijalec pa sklad že pozna.

### Posledice

- Dobro, ker prevajalnik odkrije neskladja med API in frontendom pred zagonom.
- Dobro, ker Next.js omogoča strežniško upodabljanje javnih strani.
- Dobro, ker je na voljo velik ekosistem (TanStack Query, Recharts, shadcn/ui).
- Slabo, ker TypeScript doda korak gradnje in nekaj dodatne kode za tipe.
- Slabo, ker je Next.js kompleksnejši od čistega Reacta (strežniške in odjemalske komponente).

### Potrditev

CI izvede `tsc` brez napak; po spremembi API se tipi ponovno generirajo in morebitna neskladja ustavijo gradnjo.

## Prednosti in slabosti možnosti

### React s TypeScriptom (Next.js)

- Dobro, ker je tipno varen in poznan.
- Slabo, ker je nastavitev zahtevnejša.

### React z JavaScriptom

- Dobro, ker je hitrejši začetek.
- Slabo, ker se napake v obliki podatkov pokažejo šele med izvajanjem.

### Vue ali Angular

- Dobro, ker sta zrela.
- Slabo, ker ju razvijalec ne pozna, kar bi upočasnilo razvoj.

## Dodatne informacije

Povezano: ADR-0002 (FastAPI ustvari OpenAPI specifikacijo).