# 05-Uporabniške zgodbe

| Oznaka | Funkcionalnost | Vloga | MVP |
|---|---|---|---|
| US-01 | F01 Povezava Riot računa | Igralec | da |
| US-02 | F02 Zaznava aktivne tekme | Gost | da |
| US-03 | F03 Profil nasprotne sestave | Igralec | da |
| US-04 | F04 Priporočilo builda in run | Igralec | da |
| US-05 | F05 Matchup kartica | Igralec | da |
| US-06 | F06 Profil igralnega sloga | Igralec | da |
| US-07 | F07 Učni cevovod | Administrator | da |
| US-08 | F08 Načrt igre po fazah | Igralec | |
| US-09 | F09 Tendence junglerja | Igralec | |
| US-10 | F10 Pregled po tekmi | Igralec | |
| US-11 | F11 Nadzorna plošča napredka | Igralec | |
| US-12 | F12 Ekipe in trenerski pregled | Trener | |
| US-13 | F13 Raven razlage | Igralec | |
| US-14 | F14 Baza znanja in patchi | Administrator | |
| US-15 | F15 Zgodovina analiz | Igralec | |

---

### US-01 - Povezava riot računa  
F01 - **Vloga:** Igralec

*Kot igralec želim povezati svoj Riot račun s profilom Rift_Help, da lahko analiziram svoje tekme (z enim klikom) in potrdim verodostojnost sovjega računa.*

**Acceptance criteria:**
- Ko igralec vpiše obstoječ Riot ID ("ime#oznaka") in regijo, sistem prikaže eno random privzeto profilno ikono in odšteva 10 minut.
- Ko igralec v tem času nastavi prikazano ikono in klikne "Preveri", sistem račun označi kot verificiran in ga prikaže v profilu.
- Če ikona ob preverjanju ni prava, sistem prikaže sporočilo "Ikona na računu še ni zamenjana" in omogoči ponovno preverjanje, dokler čas ne poteče.
- Če Riot ID ne obstaja v izbrani regiji, sistem prikaže "Igralca s tem Riot ID ni v regiji X" in ne začne verifikacije.
- Riot račun, ki je že verificiran pri drugem uporabniku, ni mogoče povezati.

### US-02 - Analiza aktivne tekme
F02 - **Vloga:** Gost
 
*Kot gost želim vpisati Riot ID igralca v tekmi in dobiti analizo, da lahko Rift_Help preizkusim brez registracije.*
 
**Acceptance criteria:**
- Ko gost vpiše Riot ID igralca v aktivni tekmi, sistem v največ 5 sekundah prikaže vseh 10 udeležencev s šampioni.
- Med analizo stran prikazuje napredek po korakih (zajem, profiliranje, priporočila) brez osveževanja.
- Če igralec ni v tekmi, sistem prikaže "Igralec trenutno ni v tekmi" in gumb "Poskusi znova".
- Četrta analiza z istega IP naslova v istem dnevu je zavrnjena s sporočilom o omejitvi in povabilom k registraciji.
### US-03 - Profil nasprotne sestave
F03 - **Vloga:** Igralec
 
*Kot igralec želim na prvi pogled videti, kaj je nevarno v nasprotni ekipi, da vem, na kaj paziti pri buildu in igri.*
 
**Acceptance criteria:**
- Analiza prikaže delež fizične in magične škode nasprotne ekipe v odstotkih (skupaj 100 %).
- Sistem prikaže največ 5 groženj (zdravljenje, CC, engage, burst, poke, tankovskost), razvrščenih po moči.
- Ob vsaki grožnji so našteti šampioni, ki jo povzročajo (npr. "Visoko zdravljenje: Soraka, Aatrox").
### US-04 - Priporočilo builda in run
F04 - **Vloga:** Igralec
 
*Kot igralec želim build, prilagojen nasprotni ekipi, z razlogom za vsak predmet, da razumem, zakaj kupujem kaj drugega kot običajno.*
 
**Acceptance criteria:**
- Sistem prikaže 2–3 variante builda (standardna, varna, agresivna), ki se razlikujejo v vsaj enem dokončanem predmetu.
- Vsaka varianta vsebuje rune, vsaj 3 dokončane predmete po vrstnem redu in vrstni red sposobnosti.
- Vsak predmet ima en stavek razloga, ki omenja konkretno lastnost nasprotne sestave.
- Če za šampiona ni dovolj podatkov za model, sistem uporabi pravila in to označi z "Priporočilo na podlagi pravil".
### US-05 - Matchup kartica
F05 - **Vloga:** Igralec
 
*Kot igralec želim videti, na katerih levelih je moj linijski nasprotnik močnejši, da se v boje spuščam ob pravem času.*
 
**Acceptance criteria:**
- Kartica prikaže časovnico od levela 1 do 18 za oba šampiona z označenimi okni prednosti in zaostanka.
- Kartica našteje vsaj 2 nevarni sposobnosti nasprotnika in 2–3 nasvete za linijsko fazo.
- Če sistem linijskega nasprotnika ne more določiti, igralec sam izbere nasprotnika med petimi nasprotnimi šampioni.
### US-06 - Profil igralnega sloga nasprotnika
F06 - **Vloga:** Igralec
 
*Kot igralec želim vedeti, kako moj nasprotnik običajno igra, da se pripravim na njegov slog in ne samo na njegovega šampiona.*
 
**Acceptance criteria:**
- Za vsakega nasprotnika sistem prikaže arhetip (npr. "Agresiven v linijski fazi") in število tekem, iz katerih je izračunan (največ 20).
- Pri manj kot 5 tekmah je profil označen z "nizko zaupanje".
- Profil prikaže vsaj 4 kazalnike (agresivnost, roaming, farmanje, zgodnje smrti) v primerjavi z mediano iste vloge.
- Če je igralec skril svoj profil, sistem prikaže "Profil ni javen".
### US-07 - Učni cevovod
F07 - **Vloga:** Administrator
 
*Kot administrator želim, da se modeli redno učijo na novih tekmah in da novo verzijo aktiviram po pregledu metrik, da priporočila ostanejo aktualna in se ne poslabšajo.*
 
**Acceptance criteria:**
- Cevovod se samodejno zažene enkrat na dan in zapiše čas, število novih tekem in izid (uspeh ali napaka).
- Nova verzija modela se prikaže s statusom "naučen" in metrikami (AUC, log loss).
- Modela, ki je na testnih tekmah slabši od izhodiščnega, ni mogoče aktivirati.
- Po aktivaciji naslednja analiza uporablja novo verzijo, prejšnja dobi status "umaknjen".
### US-08 - Načrt igre po fazah
F08 - **Vloga:** Igralec
 
*Kot igralec želim kratek načrt za linijsko fazo, sredino in konec igre, da vem, kaj delati tudi po tem, ko zapustim linijo.*
 
**Acceptance criteria:**
- Načrt ima tri dele (linijska faza, sredina, pozna igra), vsak z 2–3 točkami.
- Linijska faza vsebuje priporočilo za upravljanje valov minionov z razlogom.
- Sredina igre poveže vsaj en objektiv (zmaj, Herald, Baron) z oknom moči uporabnikove ekipe.
### US-09 - Tendence nasprotnega junglerja
F09 - **Vloga:** Igralec
 
*Kot igralec želim vedeti, kje nasprotni jungler najpogosteje začne in koga ganka prvega, da pravočasno postavim ward.*
 
**Acceptance criteria:**
- Sistem prikaže stran začetka (zgornja ali spodnja) in linijo prvega ganka v odstotkih tekem.
- Ob podatkih je število upoštevanih tekem; pri manj kot 5 tekmah je dodano opozorilo o nizki zanesljivosti.
- Podatki so označeni kot "tendenca iz preteklih tekem", ne kot podatek iz trenutne tekme.
### US-10 - Pregled po tekmi
F10 - **Vloga:** Igralec
 
*Kot igralec želim po tekmi primerjati načrt z dejanskim potekom, da vidim, kje sem naredil napake.*
 
**Acceptance criteria:**
- Ko je analizirana tekma končana, se v 10 minutah pojavi gumb "Odpri pregled".
- Pregled prikaže priporočeni in dejanski build drug pod drugim z označenimi razlikami.
- Graf razlike v zlatu po minutah ima označene smrti, smrti v oknih moči nasprotnika so posebej izpostavljene.
- Pregled vsebuje 3 konkretne predloge za naslednjo tekmo.
### US-11 - Nadzorna plošča napredka
F11 - **Vloga:** Igralec
 
*Kot igralec želim spremljati svoje ključne kazalnike skozi čas, da vidim, ali se izboljšujem.*
 
**Acceptance criteria:**
- Plošča prikaže CS@10, zlato na minuto, vision na minuto in smrti pred 14. minuto.
- Igralec lahko filtrira po vlogi, šampionu in obdobju (7, 30 ali 90 dni).
- Ob vsakem kazalniku je sprememba glede na prejšnje obdobje in mediana igralcev iste vloge in ranga.
- Pri manj kot 5 tekmah v obdobju plošča prikaže "Premalo tekem za trend".
### US-12 - Ekipe in trenerski pregled
F12 - **Vloga:** Trener
 
*Kot trener želim pregled nad kazalniki svojih igralcev in možnost dodajanja nalog, da lahko vodim trening na podlagi podatkov.*
 
**Acceptance criteria:**
- Trener ustvari ekipo in povabi registriranega igralca po e-pošti; igralec mora povabilo sprejeti.
- Trener vidi podatke samo igralcev s statusom "aktiven".
- Trener lahko igralcu doda nalogo z rokom, igralec jo vidi na svoji nadzorni plošči.
- Ko igralec zapusti ekipo, trener takoj izgubi dostop do njegovih podatkov.
### US-13 - Prilagoditev ravni razlage
F13 - **Vloga:** Igralec
 
*Kot nov igralec želim enostavnejši prikaz analize, da me ne zasujejo številke, ki jih še ne razumem.*
 
**Acceptance criteria:**
- Igralec v nastavitvah izbere raven začetnik, srednji ali napreden; privzeta je srednja.
- Na ravni začetnik analiza prikaže samo eno varianto builda in razloge brez številk.
- Na ravni napreden analiza prikaže vse variante, številke in pogoje za situacijske predmete.
### US-14 - Upravljanje baze znanja in patchev
F14 - **Vloga:** Administrator
 
*Kot administrator želim ob novem patchu uvoziti podatke in urediti atribute šampionov, da analize temeljijo na trenutnem stanju igre.*
 
**Acceptance criteria:**
- Gumb "Uvozi nov patch" prenese podatke iz Data Dragon in prikaže število novih in spremenjenih zapisov.
- Novi in spremenjeni šampioni so v seznamu označeni z "Preglej".
- Ocene šampionov so omejene na 0–3; druge vrednosti sistem zavrne.
- Uporabnik brez vloge administrator do teh strani nima dostopa (odgovor 403).
### US-15 - Zgodovina analiz
F15 - **Vloga:** Igralec
 
*Kot igralec želim ponovno odpreti svoje pretekle analize, da se lahko vrnem k načrtu ali ga primerjam z drugimi tekmami.*
 
**Acceptance criteria:**
- Seznam prikaže analize od najnovejše do najstarejše z datumom, šampionom in izidom tekme, 20 na stran.
- Odprta analiza je prikazana enako kot ob nastanku, z istimi priporočili.
- Uporabnik ne more odpreti analize drugega uporabnika (prikaže se "Analiza ne obstaja").



