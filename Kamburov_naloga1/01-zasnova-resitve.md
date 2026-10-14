# Zasnova rešitve

## Ime rešitve

**RIFT_HELP** - taktični vodiček/pomočnik za League of Legends na podlagi zdgodovinskih tekem. 

## Namen in uporaba ##
League ima več 170 championov, več kot 100 predmetov in run. Z vsakim patch note pa se spremeni igra (meta). Iz teh razlogov nastanejo 3 problemi:

1. **Build ni prilagojen nasprotni ekipi.** Riot že ima ingame "priporočljiv build" ki je optimalen za champa, ki ga igraš ne pa na podlagi kakšnega chmapiona ima enemy team.
2. **Igralec ne ve kdaj enemy champ dobi power spike.** Ne pozna pri katerih levelih je champion močnejši (level 6,12 in 16 na primer). Zato bori proti enemy championu v napačnem času. 
3. **Igralec ne pozna nasprotnika kot igralca.** Ali je nasprotnik hitre jeze, ali je agresiven ali je easily tilted ipd.

Rift_Help pa združi te tri podatke v konkertna priporočila builda, runes in izbrati kdaj it v boj.

## Ciljni uporabniki 
| Uporabnik | Profil | Kaj potrebuje |
|---|---|---|
| Novi igralec | Pravkar dosegel level 30, rang Iron–Silver | Kratka navodila v preprostem jeziku, malo možnosti, razlaga "zakaj" |
| Srednje izkušen igralec | Gold–Emerald, pozna osnove | Optimizacija builda proti sestavi, vpogled v slog nasprotnikov, številke |
| Trener amaterske ekipe | Vodi študentsko ali klubsko ekipo (npr. univerzitetna liga) | Pregled profilov svojih igralcev, deljenje načrtov in zapiskov |
| Administrator | Vzdrževalec sistema | Posodobitev podatkov ob novem patchu, urejanje baze znanja o šampionih |

## Uporaba 
**Scenarij A – med nalaganjem tekme.** Luka igra Jinx v Silver ligi. Ko se pojavi nalagalni zaslon, na telefonu ali drugem zaslonu odpre RiftSense in klikne "Analiziraj mojo tekmo" (njegov Riot račun je že povezan). V približno pol minute do minute dobi:
 
- opozorilo, da ima nasprotna ekipa dva vira zdravljenja (Soraka, Aatrox), zato je predmet z zmanjšanjem zdravljenja v vseh variantah builda med prvima dvema dokončanima predmetoma,
- tri variante builda (standardna, varna proti burstu, agresivna) z razlogom za vsak predmet,
- matchup kartico za bot linijo: nasprotna Leona je najnevarnejša na levelu 2 in 6, zato naj ne stoji v dosegu njenega E, ko ima support level prednosti,
- profil nasprotnega supporta iz njegovih zadnjih 20 rangiranih tekem: visoka agresivnost v prvih 5 minutah, pogost odhod iz linije po 8. minuti.

**Scenarij B – po tekmi.** Luka po porazu odpre pregled tekme. Sistem primerja priporočeni build z dejansko kupljenim in pokaže, da je dve od treh smrti v linijski fazi doživel v oknih, ko je imel nasprotnik prednost v levelu, ki ga je matchup kartica označila kot nevarnega.
 
**Scenarij C – priprava ekipe.** Trener študentske ekipe pred tedenskim treningom pregleda profile svojih petih igralcev, opazi, da ima njihov ADC nizko število pobitih minionov v prvih 10 minutah (CS@10), in mu doda nalogo za naslednji teden.

## Kratek opis delovanja
 
1. Uporabnik se registrira in poveže svoj Riot račun (Riot ID, npr. `Luka#EUNE`). Lastništvo dokaže tako, da v igralnem odjemalcu nastavi naključno izbrano profilno ikono, ki jo sistem nato preveri.
2. Ko je uporabnik v tekmi, zahteva analizo. Sistem prek uradnega Riot API (Spectator-V5) pridobi seznam 10 udeležencev, njihove šampione, summoner spelle in rune.
3. Za nasprotnike sistem prenese zadnje rangirane tekme (Match-V5, za ključne nasprotnike tudi časovnico tekme – timeline) in izračuna **profil igralnega sloga** (agresivnost, roaming, farmanje, čas smrti, vision).
4. Iz atributov šampionov v bazi znanja sistem izračuna **profil nasprotne sestave** (delež fizične in magične škode, nadzor gibanja – CC, zdravljenje, tankovskost, engage, burst).
5. **Model strojnega učenja** (LightGBM), naučen na tekmah, ki jih sistem sproti zbira, oceni kandidatne builde za izbranega šampiona glede na nasprotno sestavo. Rezultat so 2–3 najbolje ocenjene variante builda, matchup kartica in načrt po fazah. Razlogi za vsak predmet izhajajo iz prispevkov značilk modela (npr. "zdravljenje nasprotne ekipe" najbolj dvigne oceno predmeta z zmanjšanjem zdravljenja).
6. Rezultati se prikazujejo postopoma (najprej linijski nasprotnik in jungler), analiza se shrani v zgodovino uporabnika.
V ozadju teče drugi proces, **zbiranje tekem in učenje modelov**: nočni zbiralnik prenaša rangirane tekme, iz njih izračuna značilke in ponovno nauči model priporočil in model arhetipov igralcev (gručenje).
 
Jedro rešitve sta torej dva netrivialna delovna procesa: **analiza aktivne tekme** (zaznava tekme, prioritetni zajem podatkov ob omejitvah Riot API, profili, sestava in priporočila modela) in **učni cevovod** (zbiranje, značilke, učenje, vrednotenje in aktivacija modela). Podrobno v `04-arhitektura-in-tehnoloski-sklad.md`.

## Rift_Help ni 

- Ni overlay 
- Ne uporablja in game real time podatke o summs in abilities cds
- Ne prepisuje podatkov s strani op.gg ali podobnih: vir podatkov je izključno uradni Riot Games API in Data Dragon (statični podatki o šampionih in predmetih, morebitno se doda še kakšna spletna stran za statistiko). 
- Ne narekuje ene "pravilne" odločitve, ampak ponudi več možnosti z razlogi, kar zahtevajo tudi pravila Riot (orodja naj odločitve poudarijo, ne odstranijo).