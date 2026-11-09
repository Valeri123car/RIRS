# Ugotovitve – model za priporočanje buildov (testna evidenca)

Evidenca poskusov z modelom strojnega učenja za US-04 (priporočilo builda glede na nasprotno sestavo).
Vsak poskus ima: podatke, kaj napovedujemo, značilke, algoritme, način vrednotenja, rezultat in zaključek.
Novi poskusi se dodajajo na konec, starejši se ne spreminjajo.

## Izhodišče

**Kaj model napoveduje:** verjetnost zmage igralca (`win`) glede na njegovega šampiona, vlogo,
nasprotno sestavo in dokončane predmete. Ob analizi model oceni kandidatne builde (najpogostejša
jedra s 3 predmeti za šampiona) in jih razvrsti po oceni. Verjetnost ni obljuba zmage, uporablja se
samo za razvrščanje (ADR-0006).

**Pogoj za vklop (ADR-0006):** model se aktivira samo, če ima višji AUC od izhodiščnega modela brez
značilk sestave. Sicer aplikacija uporablja priporočila po pravilih (`RuleBasedRecommender`).

**Metrika:** ROC AUC (0,5 = ugibanje, 1,0 = popolna napoved).

**Podatki:** rangirane tekme challenger igralcev na EUW (League-V4 + Match-V5), patch 16.22.
Uporabljajo se samo tekme, dolge vsaj 15 minut (krajše so remake ali zgodnja predaja).

## Pregled modelov v bazi (`ml_models`)

| Verzija | Datum | Tekem | AUC | Izhodišče brez sestave | Stanje |
|---|---|---|---|---|---|
| v1 | 2026-11-08 | 287 | 0,517 | 0,550 | neaktiven |
| v2 | 2026-11-08 22:50 | 1107 | 0,526 | 0,564 | neaktiven |
| v3 | 2026-11-08 23:01 | 1260 | 0,579 | 0,594 | neaktiven |
| v4 | 2026-11-08 23:50 | 2544 (EUW + KR) | 0,582 | 0,570 | neaktiven (glej poskus 4) |
| v5 | 2026-11-09 14:20 | 6588 (EUW + KR + NA) | 0,573 | 0,579 | neaktiven (glej poskus 5) |

Vrednotenje v1–v3: ena delitev 80/20 po tekmah (`GroupShuffleSplit`). Model: LightGBM, id šampiona in
vloga kot kategoriji, surove vsote ocen sestave (0–15), 0/1 stolpec za vsak dokončan predmet
(≥ 5 pojavitev), število dokončanih predmetov (`completed_count`).

---

## Poskus 1 – značilke po predavanjih (2026-11-08, ~23:00)

**Podatki:** 1117 tekem, 11.170 igralcev.
**Vrednotenje:** 5-kratna navzkrižna validacija `GroupKFold` po tekmah (vseh 10 igralcev ene tekme je
vedno na isti strani), povprečje ± standardni odklon.

**Spremembe značilk (iz poglavja Inženiring podatkov):**

| Tehnika | Izvedba |
|---|---|
| Visoka kardinalnost kategorij | id šampiona (~170 vrednosti) → 6 razredov (Fighter, Tank, Mage, Assassin, Marksman, Support), je/ni kodiranje + fizična/magična škoda |
| Normalizacija | vsote ocen sestave 0–15 → 0–1 (min-max po znani zalogi vrednosti) |
| Odstranitev zavajajoče značilke | `completed_count` (število predmetov je posledica dolžine tekme in zmage) |
| Gradnja značilk (domena) | profil builda: deleži oznak predmetov (armor, spell_block, health, anti_heal, tenacity, …) |
| Gradnja značilk (interakcije) | oklep × fizična škoda, MR × magična škoda, anti_heal × zdravljenje, tenacity × nadzor, zdravje × burst, prebojnost × tankovskost |
| Standardizacija v cevovodu | `make_pipeline(StandardScaler(), …)` – parametri samo iz učne množice (brez uhajanja) |
| Izbira značilk (filter) | vzajemna informacija `mutual_info_classif` |

**Rezultati (napoved zmage):**

| Model | Z značilkami sestave | Brez | Prispevek sestave |
|---|---|---|---|
| LightGBM, trenutne značilke | 0,560 ± 0,010 | 0,580 | −0,020 |
| LightGBM, brez `completed_count` | 0,526 ± 0,015 | 0,564 | −0,038 |
| LightGBM, nove značilke | 0,535 ± 0,023 | 0,572 | −0,037 |
| LightGBM, nove značilke, regulariziran | 0,540 ± 0,009 | 0,579 | −0,039 |
| Logistična regresija + StandardScaler | 0,517 ± 0,023 | 0,532 | −0,016 |
| Nevronska mreža MLP 32-16 + StandardScaler | 0,525 ± 0,016 | 0,551 | −0,027 |

Vzajemna informacija: vse značilke ≤ 0,013 (na ravni šuma ocenjevalnika).

**Dodatno – napoved nakupa predmeta** (ali iz sestave lahko napovemo, kaj challengerji kupijo):
nakup je skoraj v celoti določen s šampionom (AUC 0,91–0,997 za 25 najpogostejših predmetov);
sestava doda od −0,005 do +0,001.

**Zaključek:** sestava v vseh kombinacijah napoved poslabša. Razpršenost čez delitve (±0,01–0,02) je
večja od razlik med v1 in v2, zato ena delitev ni zanesljiva ocena. Nevronska mreža ni izbrana
(slabša od LightGBM; po predavanju se velike mreže na majhnih množicah pretrenirajo).

---

## Poskus 2 – več ciljev, značilk in algoritmov (2026-11-08, ~23:10)

**Podatki:** 1260 tekem, 12.600 igralcev. **Vrednotenje:** `GroupKFold` 5.

**Algoritmi:** logistična regresija, naivni Bayes, kNN (k = 101), naključni gozd, ExtraTrees,
HistGradientBoosting, LightGBM (regulariziran), MLP 16 (L2 0,1), MLP 64-32 (L2 0,05).
Pri nevronskih mrežah: StandardScaler v cevovodu, L2 regularizacija in zgodnja ustavitev
(sklearn nima dropouta).

**Nove značilke:** ciljno kodiranje šampiona (zglajen win rate, izračunan **samo na učnem foldu**),
sestava lastne ekipe, razlika med ekipama, deleži razredov v ekipi.

| Naloga | Značilke | Najboljši AUC | Algoritem |
|---|---|---|---|
| Zmaga igralca | šampion | 0,512 | kNN |
| | + nasprotna sestava | 0,515 | naivni Bayes |
| | + lastna sestava in razlika | 0,528 | kNN |
| | + build in interakcije | **0,552** | ExtraTrees |
| | vse skupaj | 0,548 | HistGB |
| Zmaga ekipe (1 vrstica na ekipo) | obe sestavi | 0,531 | HistGB |
| | + win rate šampionov | 0,534 | HistGB |
| Nakup situacijskega predmeta (517 parov šampion–predmet s 15–85 % nakupov, 52.706 vrstic) | predhodna verjetnost + oznake | 0,714 | LightGBM |
| | + sestava in interakcije oznaka × sestava | 0,714 (+0,0003) | LightGBM |

MLP ni bil najboljši pri nobeni nalogi.

**Preverjanje "build pomaga":**

| Igralci | Samo šampion | + sestava + build |
|---|---|---|
| vsi (12.600) | 0,509 | 0,552 |
| ≥ 3 dokončani predmeti (6478) | 0,522 | 0,526 |
| ≥ 4 dokončani predmeti (2470) | 0,547 | 0,550 |

Zmagovalci imajo povprečno 2,77 dokončanega predmeta, poraženci 2,45.

**Zaključek:** navidezni prispevek builda je **skrito uhajanje podatkov**. Končni build je posledica
stanja tekme (kdor vodi, ima več zlata in drugačne predmete), ne vzrok zmage. Ko primerjamo igralce s
podobnim številom predmetov, prispevek izgine (+0,004). Iz teh podatkov boljšega modela ni.

---

## Poskus 3 – učna krivulja (2026-11-08, ~23:20)

**Vprašanje:** ali bi več tekem pomagalo? **Postopek:** isti testni foldi, učenje na 25/50/75/100 %
učnih tekem, LightGBM (regulariziran).

| Delež | Učnih tekem | Šampion | + nasprotna sestava | + lastna sestava | + build (≥ 3 predmeti) | Prispevek builda |
|---|---|---|---|---|---|---|
| 0,25 | 252 | 0,505 | 0,481 | 0,485 | 0,495 | +0,005 |
| 0,50 | 505 | 0,494 | 0,497 | 0,512 | 0,527 | +0,002 |
| 0,75 | 758 | 0,508 | 0,497 | 0,492 | 0,506 | +0,003 |
| 1,00 | 1011 | 0,506 | 0,491 | 0,501 | 0,516 | +0,007 |

**Zaključek:** krivulja je ravna (vse okoli 0,50 ± 0,02). V obsegu do ~1000 tekem ni zaznavnega
trenda, zato je morebitni učinek sestave manjši od šuma. Ocena potrebne količine: razliko 2 odstotnih
točk v win rateu (npr. MR predmet proti AP sestavi) zaznamo pri 2 σ šele pri ~2500 igrah na skupino
(SE = 0,5/√n), kar je za posamezen par šampion–predmet reda več deset tisoč tekem.

---

## Poskus 4 – več podatkov in druga regija (2026-11-08, ~23:50)

**Podatki:** dodaten zajem 23:18–23:48, vzporedno EUW in **KR** (Riot omejuje klice po regionalnem
usmerjevalniku: EUW → `europe`, KR → `asia`, zato dve regiji podvojita hitrost na ~2800 tekem/h).
Skupaj 2578 tekem, uporabnih 2544 (EUW 1926, KR 618), patchi 16.20 (264), 16.21 (1345), 16.22 (935).

**Model v4** (ena delitev 80/20, kot v kodi): AUC 0,582 > izhodišče 0,570 – prvič nad izhodiščem.

**Preverjanje s 5-kratno `GroupKFold`:**

| Značilke | S sestavo | Brez sestave | Prispevek sestave |
|---|---|---|---|
| kot v produkciji (v4) | 0,579 ± 0,012 | 0,578 | +0,0005 |
| brez `completed_count` | 0,548 ± 0,009 | 0,563 | −0,015 |
| nove značilke (poskus 1), regulariziran LightGBM | 0,574 ± 0,014 | 0,583 | −0,009 |
| samo EUW (1926 tekem) | 0,567 ± 0,011 | 0,579 | −0,012 |
| samo KR (618 tekem) | 0,537 ± 0,004 | 0,553 | −0,016 |

**Zaključek:** zmaga v4 nad izhodiščem je posledica ugodne delitve (prispevek +0,0005 je znotraj
šuma ±0,012). Model zato **ni aktiviran**. To pokaže slabost trenutnega pogoja za vklop: z
`--activate` bi se v4 vklopil, čeprav ni boljši – zato je zamenjava ene delitve z `GroupKFold` v kodi
(naslednji korak 4) potrebna, preden se kateri koli model aktivira. Dvig AUC na ~0,58 izvira iz
`completed_count` (uhajanje stanja tekme, poskus 2), ne iz sestave. Mešanje regij in patchev ne pomaga:
tudi ločeno po regijah sestava napoved poslabša.

---

## Poskus 5 – 6588 tekem iz treh regij, celotne metrike (2026-11-09, ~14:20)

**Podatki:** zajem 2026-11-09 13:05–14:00 vzporedno na treh regionalnih usmerjevalnikih
(EUW → `europe`, KR → `asia`, NA → `americas`; ~75 tekem/min). EUNE deli `europe` z EUW, zato
zajema ne pospeši in je bil po nekaj minutah zamenjan z NA. Skupaj 6669 tekem, uporabnih (≥ 15 min)
**6588** = 65.880 igralcev (EUW 3276, KR 1974, NA 1315, EUNE 23), patchi 16.14–16.22. Delež zmag
je točno 0,500 (vsaka tekma ima 5 zmagovalcev in 5 poražencev).

**Model v5** (`python -m app.ml`, ena delitev 80/20): AUC 0,5725 < izhodišče 0,5785 → **neaktiven**.

**Vrednotenje:** 5-kratna `GroupKFold` po tekmah (igralci iste tekme so vedno v isti delitvi), iste
značilke in parametri LightGBM kot v produkciji. Napovedi vseh delitev so združene; prag za
razred je 0,5. Naivni model (vedno 0,5) ima AUC 0,500, log loss 0,6931 in Brier 0,2500.

| Značilke | AUC (± odklon) | Log loss | Brier | Točnost | Preciznost | Priklic | F1 |
|---|---|---|---|---|---|---|---|
| vse (v5) | 0,5811 ± 0,0057 | 0,6841 | 0,2455 | 0,559 | 0,555 | 0,597 | 0,575 |
| brez sestave (izhodišče) | **0,5846 ± 0,0035** | **0,6818** | **0,2444** | **0,562** | 0,557 | 0,608 | 0,581 |
| brez `completed_count` | 0,5638 ± 0,0060 | 0,6878 | 0,2473 | 0,548 | 0,549 | 0,537 | 0,543 |
| brez `completed_count` in sestave | 0,5727 ± 0,0022 | 0,6851 | 0,2460 | 0,551 | 0,553 | 0,538 | 0,545 |
| samo šampion + položaj | 0,5148 ± 0,0048 | 0,6950 | 0,2509 | 0,510 | 0,510 | 0,507 | 0,509 |

**Matrika zmede** (65.880 igralcev, prag 0,5; vrstice = dejansko, stolpci = napovedano):

| v5 (vse značilke) | napoved poraz | napoved zmaga |
|---|---|---|
| **poraz** (32.940) | TN 17.176 | FP 15.764 |
| **zmaga** (32.940) | FN 13.264 | TP 19.676 |

| Izhodišče brez sestave | napoved poraz | napoved zmaga |
|---|---|---|
| **poraz** (32.940) | TN 16.972 | FP 15.968 |
| **zmaga** (32.940) | FN 12.898 | TP 20.042 |

Oba modela pravilno uvrstita le ~56 % igralcev. Napaki sta skoraj simetrični, z rahlim nagibom k
napovedi zmage (priklic 0,60 > preciznost 0,56).

**Po regijah** (vsaka regija posebej, 5-kratna GroupKFold):

| Regija | Igralcev | AUC vse | AUC brez sestave | Prispevek sestave |
|---|---|---|---|---|
| EUW | 32.760 | 0,5773 | 0,5828 | −0,0055 |
| KR | 19.740 | 0,5624 | 0,5670 | −0,0047 |
| NA | 13.150 | 0,5441 | 0,5601 | −0,0160 |

**Učna krivulja** (naključni podvzorci tekem, seme 7):

| Tekem | AUC vse | AUC brez sestave | Prispevek sestave |
|---|---|---|---|
| 1000 | 0,5517 ± 0,0127 | 0,5610 | −0,0093 |
| 2500 | 0,5606 ± 0,0061 | 0,5722 | −0,0116 |
| 4000 | 0,5769 ± 0,0105 | 0,5803 | −0,0034 |
| 6588 | 0,5811 ± 0,0057 | 0,5846 | −0,0036 |

**Zaključek:**

- Sestava nasprotnikov napoved še vedno rahlo **poslabša** (−0,0036 pri odklonu ±0,0057). Pri vseh
  metrikah je izhodišče brez sestave enako dobro ali boljše, zato v5 **ni aktiviran** in priporočilo
  ostane po pravilih.
- Več podatkov pomaga obema modeloma (AUC 0,55 → 0,58), negativni prispevek sestave pa se z več
  podatki manjša (−0,012 → −0,004). To pomeni, da 7 značilk sestave pri manj podatkih povzroča
  prekomerno prilagajanje, ne pa, da sestava ni pomembna. Pozitivnega učinka tudi pri 6588 tekmah ni.
- Napovedna moč prihaja skoraj v celoti iz builda: samo šampion in položaj dasta 0,515, predmeti
  dvignejo AUC na ~0,57, `completed_count` pa še za ~0,01–0,02 (uhajanje stanja tekme, poskus 2).
- Odklon med delitvami se je s 6588 tekmami zmanjšal na ±0,004–0,006 (pri 2544 tekmah ±0,012), zato
  so primerjave zdaj zanesljivejše kot v poskusih 1–4.
- Regije se ne smejo kar mešati: NA je pri enakem modelu precej slabša (0,544). Pri skupnem učenju
  je smiselno dodati regijo kot značilko.

---

## Zakaj je napoved zmage tako težka (51 % win rate)

Matchmaking sestavlja tekme tako, da ima vsaka ekipa ~50 % možnosti, igralci pa dolgoročno ~50–51 %
win rate. Posledice:

- Informacije pred tekmo (šampioni, sestava) po zasnovi nosijo malo signala; večino izida odloči
  igra sama. Tudi profesionalni modeli iz izbire šampionov dosežejo le ~0,55–0,60 AUC na zelo velikih
  množicah.
- Na **vprašanje, ali je build pravilen glede na sestavo**, to ne vpliva neposredno – primerjamo
  igralce istega šampiona z različnimi buildi. Učinek dobre izbire je pa majhen (nekaj odstotnih
  točk), zato potrebuje veliko podatkov.
- Nizek AUC zato ni napaka v kodi, ampak lastnost domene.

## Kaj bi pomagalo (naslednji koraki)

1. **Nakupi iz časovnic:** zbiralnik časovnice že prenaša, shrani pa samo `cs_at_10`, `xp_at_10`,
   `gold_at_15`, `deaths_before_14`. Shranjevanje dogodkov `ITEM_PURCHASED` (predmet + čas) omogoči
   build ob enaki točki tekme (npr. prvi dokončani predmet, build pri 15. minuti) in odpravi uhajanje
   iz poskusa 2.
2. **Drugačen cilj:** namesto zmage napovedovati razliko v zlatu/škodi v naslednjih minutah po
   nakupu – bolj neposreden in manj šumen signal.
3. **Več tekem:** reda 10.000+ (pri razvojnem ključu ~1300 tekem/h na regijo, z dvema regijama
   ~2800/h → več nočnih zajemov). Pri mešanju regij in patchev dodati regijo in patch kot značilki.
4. **Vrednotenje v kodi:** zamenjati eno delitev s `GroupKFold` in v metrike zapisati povprečje ± odklon;
   pogoj za vklop naj zahteva, da je prispevek sestave večji od odklona (poskus 4 pokaže, zakaj).
