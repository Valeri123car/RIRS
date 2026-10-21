---
status: sprejeto
date: 2026-10-21
decision-makers: Valeri Kamburov
---

# Strojno učenje v MVP, pravila kot rezerva

## Kontekst in problem

Jedro Rift_Help je priporočilo builda glede na nasprotno sestavo in uvrstitev nasprotnikov v arhetipe igralnega sloga. Ali naj priporočila temeljijo na ročnih pravilih, na modelu strojnega učenja ali na kombinaciji?

## Dejavniki odločitve

- Povezav med sestavo, buildom in izidom je preveč, da bi jih ročno zajeli s pravili.
- Priporočila morajo biti razložljiva (razlog za vsak predmet).
- Za nove šampione ali na začetku patcha podatkov ni dovolj (hladni zagon).
- Model ne sme v produkcijo, če je slabši od izhodišča.

## Obravnavane možnosti

- Model strojnega učenja (LightGBM, Gaussian Mixture) z rezervnimi pravili
- Samo ročna pravila
- Samo model strojnega učenja

## Odločitev

Izbrana možnost: "Model strojnega učenja z rezervnimi pravili", ker model zajame povezave, ki jih pravila ne, pravila pa zagotovijo priporočilo tudi takrat, ko model nima dovolj podatkov.

### Posledice

- Dobro, ker se priporočila izboljšujejo z novimi tekmami brez ročnega dela.
- Dobro, ker LightGBM vrne prispevke značilk (SHAP), iz katerih nastanejo razlogi za predmete.
- Dobro, ker oba načina tečeta za istim vmesnikom `Recommender`, zato frontend ne ve, kateri je bil uporabljen.
- Dobro, ker vsako priporočilo hrani `model_id`, zato je sledljivo do verzije modela.
- Slabo, ker zahteva učni cevovod, vrednotenje in upravljanje verzij modelov (`ml_models`).
- Slabo, ker izid tekme močno določa spretnost igralca; ocena modela se zato uporablja za razvrščanje buildov, ne kot obljubljena verjetnost zmage.

### Potrditev

Nova verzija modela priporočil se lahko aktivira samo, če ima na testnih tekmah višji AUC od izhodiščnega modela brez značilk sestave. Delež priporočil, narejenih s pravili, je prikazan v administraciji.

## Prednosti in slabosti možnosti

### Model z rezervnimi pravili

- Dobro, ker združi natančnost modela in zanesljivost pravil.
- Slabo, ker je treba vzdrževati oba.

### Samo pravila

- Dobro, ker so preprosta in v celoti razložljiva.
- Slabo, ker ne zajamejo kombinacij več dejavnikov in jih je treba ročno popravljati ob vsakem patchu.

### Samo model

- Dobro, ker je ena sama pot.
- Slabo, ker za nove šampione ne da priporočila ali da nezanesljivo.

## Dodatne informacije

Povezano: ADR-0005 (shranjevanje tekem), ADR-0007 (več variant builda). Pred to odločitvijo je bilo strojno učenje načrtovano kot kasnejša nadgradnja.