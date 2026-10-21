# 02 – Funkcionalnosti in obseg

## Uporabniške vloge

### Gost (neprijavljen uporabnik)

**Lahko:** išče igralce po Riot ID in vidi javni povzetek (rang, zadnje tekme, šampioni), zažene do 3 analize aktivne tekme na dan (na IP naslov), vidi rezultat, dokler ima odprto stran.

**Nima pravic:** shranjevanja analiz, povezave Riot računa, nadzorne plošče, pregleda po tekmi in članstva v ekipah.

### Igralec (registriran uporabnik)

**Lahko:** vse kot gost z višjo kvoto (30 analiz na dan), poveže in verificira Riot račune, z enim klikom analizira lastno tekmo, vidi zgodovino analiz, pregled po tekmi in nadzorno ploščo napredka, nastavi raven razlage in glavno vlogo, skrije svoj profil sloga (opt-out), sprejme povabilo v ekipo.

**Nima pravic:** vpogleda v podatke drugih uporabnikov, urejanja baze znanja, upravljanja uporabnikov.

### Trener

**Lahko:** vse kot igralec, ustvari ekipo in povabi igralce, vidi profile, nadzorne plošče in analize članov, ki so povabilo sprejeli, piše zapiske in naloge ter deli načrt igre z ekipo.

**Nima pravic:** vpogleda v igralce izven svoje ekipe, urejanja analiz ali nastavitev igralcev, urejanja baze znanja in upravljanja uporabnikov.

### Administrator

**Lahko:** upravlja uporabnike in vloge, uvozi podatke novega patcha (Data Dragon), ureja atribute šampionov in oznake predmetov, spremlja zbiralnik tekem in porabo kvote Riot API, pregleda metrike naučenih modelov in aktivira novo verzijo modela.

**Nima pravic:** prijave v imenu drugega uporabnika, vpogleda v gesla (shranjena so zgoščena), branja zasebnih zapiskov trenerjev.

## Predvidene funkcionalnosti

**MVP** = del prve delujoče različice. **Domensko** = značilno za to rešitev, ne zgolj CRUD.

| ID | Funkcionalnost | MVP | Domensko |
|---|---|---|---|
| F01 | Registracija, prijava in povezava Riot računa z verifikacijo profilne ikone | MVP | |
| F02 | Zaznava aktivne tekme in zajem udeležencev | MVP | da |
| F03 | Profil nasprotne sestave | MVP | da |
| F04 | Priporočilo builda in run z modelom strojnega učenja | MVP | da |
| F05 | Matchup kartica za linijo s časovnico moči | MVP | da |
| F06 | Profil igralnega sloga nasprotnika (gručenje) | MVP | da |
| F07 | Zbiranje tekem in učni cevovod | MVP | da |
| F08 | Načrt igre po fazah | | da |
| F09 | Tendence nasprotnega junglerja | | da |
| F10 | Pregled po tekmi (načrt proti dejanskemu poteku) | | da |
| F11 | Osebna nadzorna plošča napredka | | da |
| F12 | Ekipe in trenerski pregled | | |
| F13 | Prilagoditev ravni razlage | | |
| F14 | Upravljanje baze znanja in patchev | | |
| F15 | Zgodovina analiz | | |

### Opis funkcionalnosti

- **F01 – Povezava Riot računa:** uporabnik v odjemalcu nastavi naključno izbrano profilno ikono, sistem jo preveri prek Summoner-V4 (nadomestek za Riot Sign On, ki zahteva produkcijski ključ).
- **F02 – Zaznava aktivne tekme:** prek Spectator-V5 sistem dobi 10 udeležencev (šampioni, spelli, rune) in asinhrono zažene analizo s prikazom napredka.
- **F03 – Profil nasprotne sestave:** delež fizične/magične škode, CC, zdravljenje, tankovskost, engage, burst in poke, prikazano kot seznam groženj (npr. "Visoko zdravljenje: Soraka, Aatrox"). Isti vektor je vhod v model F04.
- **F04 – Priporočilo builda in run:** model LightGBM oceni kandidatne builde glede na šampiona, vlogo in sestavo nasprotnikov; prikažejo se 2–3 najbolje ocenjene variante, razlog za vsak predmet pa izhaja iz prispevkov značilk (SHAP). Ko za šampiona ni dovolj podatkov, sistem uporabi pravila.
- **F05 – Matchup kartica:** časovnica moči od levela 1 do 18 za oba šampiona, okna prednosti in zaostanka, nevarne sposobnosti in pristop v linijski fazi.
- **F06 – Profil igralnega sloga:** iz zadnjih do 20 rangiranih tekem (uboji in smrti pred 14. min, roaming, CS@10, razlika v zlatu, vision) model gručenja (Gaussian Mixture) igralca uvrsti v arhetip (npr. agresiven, farmer, roamer) z verjetnostjo pripadnosti.
- **F07 – Zbiranje tekem in učni cevovod:** nočni zbiralnik prenaša rangirane tekme in časovnice, izračuna značilke, ponovno nauči oba modela in shrani metrike; nova verzija se uporabi šele, ko jo administrator aktivira.
- **F08 – Načrt igre po fazah:** linijska faza (upravljanje valov minionov glede na matchup in tveganje gankov), sredina igre (objektivi glede na trenutke moči), pozna igra (pozicioniranje glede na grožnje).
- **F09 – Tendence junglerja:** iz preteklih tekem stran začetka in liniji prvega ganka, prikazano kot statistična tendenca.
- **F10 – Pregled po tekmi:** primerjava priporočenega in dejanskega builda, smrti v oknih moči nasprotnika, razlika v zlatu po minutah.
- **F11 – Nadzorna plošča napredka:** trendi CS@10, zlata/min, vision/min in zgodnjih smrti v primerjavi z mediano iste vloge in ranga.
- **F12 – Ekipe:** trener ustvari ekipo, vidi profile članov ter jim dodaja zapiske in naloge.
- **F13 – Raven razlage:** začetnik dobi eno varianto in preproste razlage, napreden igralec vse variante in številke.
- **F14 – Baza znanja in patchi:** administrator uvozi nov patch, uredi atribute šampionov in predmetov ter sproži ponoven izračun.
- **F15 – Zgodovina analiz:** seznam shranjenih analiz, ki jih lahko uporabnik ponovno odpre.

## Kasnejše nadgradnje

1. **Samodejno ponovno učenje ob novem patchu** s sledenjem eksperimentom (MLflow) in A/B primerjavo verzij modela.
2. **Namizni spremljevalec** (Electron/Tauri), ki med tekmo bere Live Client Data API in sproti prilagaja priporočila iz podatkov, vidnih v igri. (TO JE SPORNO)
3. **Razlagalec z jezikovnim modelom**, ki odgovarja na vprašanja o analizi samo iz njenih podatkov.
4. **Iskanje podobnih igralcev** (pgvector): s katerimi buildi so zmagovali igralci s podobnim profilom.
5. **Obvestila ob začetku tekme** (PWA) s samodejnim zagonom analize.
6. **Svetovalec pri izbiri šampionov** glede na že izbrane šampione obeh ekip.
7. **Prijava z Riot Sign On** po pridobitvi produkcijskega ključa.
8. **Podpora drugim načinom igre in regijam** (npr. ARAM).

## Izven obsega (out of scope)

- Prekrivni sloj (overlay) v igri ali poseganje v igralni odjemalec.
- Podatki, ki jih igralec v igri ne vidi (časovniki sposobnosti, položaj nasprotnikov v realnem času).
- Strganje spletnih strani (op.gg, u.gg ...) – samo uradni Riot API in Data Dragon.
- Lastna lestvica, MMR ali ELO kalkulator (prepovedano s pravili Riot).
- Analiza igralcev, ki jih igra namenoma skriva.
- Plačljive naročnine in plačilni sistem.
- Teamfight Tactics, Valorant in način Arena.
- Native mobilna aplikacija (spletna je odzivna).
- Klepet in družabne funkcije.