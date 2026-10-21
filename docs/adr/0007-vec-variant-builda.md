---
status: sprejeto
date: 2026-10-21
decision-makers: Valeri Kamburov
---

# Več variant builda z razlogi namesto enega "optimalnega"

## Kontekst in problem

Model lahko vrne en najbolje ocenjen build. Ali naj Rift_Help igralcu prikaže en "pravilen" build ali več možnosti, med katerimi izbere sam?

## Dejavniki odločitve

- Pravila Riot ne odobrijo aplikacij, ki narekujejo odločitve igralcev; orodja naj odločitve poudarijo in ponudijo več izbir.
- Pravila Riot zahtevajo, da orodja povečajo raznolikost odločitev (buildov).
- Ciljni uporabniki se učijo; razumeti morajo, zakaj je predmet priporočen.
- Igralci imajo različen slog in tveganje, ki ga sprejmejo.

## Obravnavane možnosti

- 2–3 variante (standardna, varna, agresivna) z razlogom za vsak predmet
- En optimalen build
- Seznam vseh buildov z oceno

## Odločitev

Izbrana možnost: "2–3 variante z razlogom za vsak predmet", ker je skladna s pravili Riot, ohranja odločitev pri igralcu in ga hkrati uči, zakaj je predmet primeren proti tej sestavi.

### Posledice

- Dobro, ker je aplikacija skladna s pravili Riot in primerna za registracijo produkta.
- Dobro, ker igralec izbere varianto glede na svoj slog in potek tekme.
- Dobro, ker razlogi pomagajo igralcu, da se nauči prilagajanja buildov.
- Slabo, ker je prikaz obsežnejši; za začetnike je zato na voljo raven razlage z eno varianto (F13).
- Slabo, ker morajo biti variante med seboj dovolj različne, kar zahteva dodatno logiko pri izbiri.

### Potrditev

Test preveri, da se vrnjene variante razlikujejo v vsaj enem dokončanem predmetu in da ima vsak predmet razlog.

## Prednosti in slabosti možnosti

### 2–3 variante z razlogi

- Dobro, ker je skladno s pravili in poučno.
- Slabo, ker je prikaz bolj zapleten.

### En optimalen build

- Dobro, ker je najpreprostejši za prikaz.
- Slabo, ker narekuje odločitev in je v nasprotju s pravili Riot.

### Vsi buildi z oceno

- Dobro, ker je popolnoma pregleden.
- Slabo, ker začetnika zasuje z možnostmi.

## Dodatne informacije

- Pravila: https://developer.riotgames.com/docs/lol (Game Integrity, Unapproved Use Cases)
- Povezano: ADR-0006.