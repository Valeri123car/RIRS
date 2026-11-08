# RIFT_HELP

Taktični pomočnik za League of Legends. Na podlagi aktivne tekme in zgodovine nasprotnikov predlaga build, rune in okna za boj (power spike), ter pokaže profil igralnega sloga nasprotnikov.

Podatki izključno iz uradnega **Riot Games API** in **Data Dragon**.

## Tehnološki sklad

| Del | Tehnologije |
|---|---|
| Frontend | Next.js, React, TypeScript, Tailwind CSS |
| Backend | Python, FastAPI, SQLAlchemy, Alembic, Celery |
| ML | LightGBM, scikit-learn |
| Baza | PostgreSQL, Redis |
| Razvoj | Docker Compose, npm, uv |

## Struktura

```
backend/    FastAPI API, Celery delavci, ML modul
frontend/   Next.js aplikacija
docs/       zasnova, uporabniške zgodbe, wireframes, ADR
design/     HTML koncepti zaslonov (vizualni stil)
```

## Lokalni zagon

Predpogoji: Docker + Docker Compose, (opcijsko) Riot API ključ z [developer.riotgames.com](https://developer.riotgames.com).

```bash
git clone https://github.com/Valeri123car/RIRS.git
cd RIRS
cp .env.example .env        # po potrebi vpiši RIOT_API_KEY
docker compose up -d --build
```

| Storitev | Naslov |
|---|---|
| Frontend | http://localhost:3000 |
| API dokumentacija | http://localhost:8989/docs |
| PostgreSQL | localhost:5432 |
| Redis | localhost:6379 |

Če je kateri od portov zaseden, ga spremeni v `.env` (`FRONTEND_PORT`, `API_PORT`, `POSTGRES_PORT`, `REDIS_PORT`).
Ustavitev: `docker compose down` (z `-v` se izbriše tudi baza).

### Riot API

Riot API kliče samo modul `backend/app/riot/` (Account-V1, Summoner-V4, Spectator-V5, League-V4,
Match-V5).

- `RIOT_API_MODE=fixtures` (privzeto) vrača sintetične odgovore v obliki Riot API iz
  `backend/app/riot/fixtures/`, zato aplikacija deluje brez ključa. Na voljo so igralci platforme
  `eun1` (npr. `Luka#EUNE` je v aktivni tekmi, `Miha#EUNE` ni) in `Sara#EUW` na `euw1`. Za
  zbiralnik tekem ima `euw1` challenger ligo s 4 igralci in 3 tekme s časovnicami.
- `RIOT_API_MODE=live` kliče pravi Riot API in zahteva `RIOT_API_KEY` (razvojni ključ velja 24 ur)
  ter `REDIS_URL`. Klici so omejeni prek Redis na 20 / 1 s in 100 / 2 min za vsako regijo, skupno
  vsem procesom; ob `429` klient počaka `Retry-After` in poskusi znova.

### Prijava

API ima `POST /auth/register`, `/auth/login`, `/auth/refresh`, `/auth/logout` in `GET /auth/me`
(podrobnosti na `/docs`). Gesla so zgoščena z Argon2id. Prijava vrne kratkoživ dostopni žeton
(JWT, 15 min, glava `Authorization: Bearer ...`), osvežilni žeton (14 dni) pa je v piškotku
`HttpOnly` s potjo `/auth`. Potrebna je nastavitev `JWT_SECRET` (vsaj 32 znakov, glej `.env.example`);
v produkciji nastavi še `COOKIE_SECURE=true`. Z istega IP naslova je dovoljenih največ 10 poskusov
prijave v 15 minutah in 5 registracij na uro (nato 429 z glavo `Retry-After`; števci so v Redis).

**Preizkus povezave Riot računa (US-01) brez ključa:** registriraj se na `/registracija`, na
`/profil` vpiši `Luka#EUNE` (regija EUNE) in klikni *Začni verifikacijo*. V načinu `fixtures` se
pokaže gumb *Simuliraj zamenjavo ikone*, ki nadomesti zamenjavo ikone v odjemalcu igre; nato klikni
*Preveri*. `Sara#EUW` na regiji EUNE pokaže sporočilo, da igralca ni v regiji.

### Backend brez Dockerja

Predpogoj: [uv](https://docs.astral.sh/uv/). Baza teče v Dockerju (`docker compose up -d postgres redis`).

```bash
cd backend
uv sync                                            # namesti odvisnosti
export DATABASE_URL=postgresql+psycopg://rift:rift-dev-geslo@127.0.0.1:5432/rift_help
uv run alembic upgrade head                        # migracije
uv run uvicorn app.main:app --reload --port 8989   # API na http://127.0.0.1:8989
uv run ruff check .                                # linter
```

V Dockerju API migracije uveljavi sam ob zagonu.

**Delavec (Celery)** izvaja analize (klici Riot API). V Dockerju je storitev `worker`; lokalno ga
zaženeš z `uv run celery -A app.worker worker --loglevel=info` (potrebuje `REDIS_URL`). Analizo
zažene `POST /analyses` (vrne 202 in ID), stanje vrne `GET /analyses/{id}`. Napredek v živo pošilja
SSE tok `GET /analyses/{id}/events` (dogodek `progress` ob vsakem koraku, do končnega stanja), npr.
`curl -N http://127.0.0.1:8989/analyses/<id>/events`. Gost lahko zažene največ 3 analize na dan z
istega IP naslova (četrta vrne 429); števec je v Redis, prijavljeni uporabniki omejitve nimajo.

**Uvoz šampionov in predmetov** iz Data Dragon (potrebna je internetna povezava, ključ ne):

```bash
uv run python -m app.ddragon                     # zadnji patch
uv run python -m app.ddragon --version 16.22.1   # izbran patch
docker compose exec api python -m app.ddragon    # v Dockerju
```

Ukaz izpiše število novih, spremenjenih in nespremenjenih zapisov. Uvozijo se samo predmeti za
Summoner's Rift. Ocene šampionov (CC, zdravljenje, engage ...) se izpeljejo iz Riotovih oznak in
ročnih popravkov v `backend/app/ddragon/champion_overrides.json`. Ponovni uvoz posodobi imena,
cene, razrede šampionov (Tank, Mage ...) in oznako dokončanih predmetov, ne povozi pa ocen in
oznak, ki jih ureja administrator. Po nadgradnji baze (`alembic upgrade head`) uvoz poženi znova,
saj priporočila builda potrebujejo razrede in dokončane predmete.

**Priporočila builda (US-04):** analiza po profilu nasprotne sestave sestavi 3 variante builda
(standardna, varna, agresivna) z runami, dokončanimi predmeti in vrstnim redom sposobnosti. Dokler
model ni naučen, se uporabijo pravila v `backend/app/recommend/rules.py` (priporočilo je označeno
z "Priporočilo na podlagi pravil").

**Zbiralnik tekem (US-07)** prenaša rangirane tekme za učenje modelov, samo prek uradnega Riot API
(ADR-0001): challenger liga platforme (League-V4) → zadnje rangirane solo tekme teh igralcev
(Match-V5, `queue=420`) → tekma in časovnica. Tekme se trajno shranijo v `matches` (celoten odgovor
v `raw`) in `match_participants` (statistika, predmeti in značilke zgodnje igre iz časovnice:
`cs_at_10`, `xp_at_10`, `gold_at_15`, `deaths_before_14`); igralci se dodajo v `riot_accounts` brez
uporabnika. Tekme, ki so že v bazi, se ne prenesejo znova (ADR-0005). Vsak zagon se zapiše v
`collector_runs` (začetek, konec, število igralcev in novih tekem, `success`/`error` s sporočilom).

```bash
uv run python -m app.collector                         # z nastavitvami iz .env
uv run python -m app.collector --players 2 --matches 5 # majhen preizkus
uv run python -m app.collector --platform eun1 --per-player 10 --no-timelines
docker compose exec api python -m app.collector        # v Dockerju
```

Samodejno se zažene enkrat na dan: storitev `beat` (Celery beat) ob `COLLECTOR_HOUR_UTC` pošlje
nalogo `collector.run`, izvede jo `worker`. Lokalno: `uv run celery -A app.worker beat --loglevel=info`
poleg delavca. Velikost zagona omejujejo `COLLECTOR_MAX_PLAYERS`, `COLLECTOR_MATCHES_PER_PLAYER` in
`COLLECTOR_MAX_NEW_MATCHES` (glej `.env.example`). Klici gredo skozi skupni Redis omejevalnik, zato
privzeti zagon (do 100 novih tekem s časovnicami ≈ 220 klicev) z razvojnim ključem traja približno
5 minut. Zadnje zagone vidiš z
`docker compose exec postgres psql -U rift -d rift_help -c "select * from collector_runs order by id desc limit 5"`.

**Testi:** `uv run pytest`. Testi baze se izvedejo samo, če je nastavljen `TEST_DATABASE_URL` (migrirana baza; podatki se po vsakem testu razveljavijo). Uporabi ločeno bazo, da testi ne trčijo v podatke, ki jih ustvariš v aplikaciji (npr. povezan Riot račun):

```bash
docker compose exec postgres psql -U rift -d rift_help -c "CREATE DATABASE rift_help_test OWNER rift;"
export TEST_DATABASE_URL=postgresql+psycopg://rift:rift-dev-geslo@127.0.0.1:5432/rift_help_test
DATABASE_URL=$TEST_DATABASE_URL uv run alembic upgrade head
uv run pytest
```

Podobno test omejevalnika klicev na pravem Redisu zahteva `TEST_REDIS_URL` (sicer se uporabi `fakeredis`):

```bash
TEST_REDIS_URL=redis://:rift-dev-geslo@127.0.0.1:6379/0 uv run pytest tests/riot
```

**Nova migracija** po spremembi modelov: `uv run alembic revision --autogenerate -m "opis"`; preglej ustvarjeno datoteko v `alembic/versions/`.

> Uporabi `127.0.0.1` namesto `localhost`: ta lahko kaže na IPv6 (`::1`), kjer baza ne posluša.

### Frontend brez Dockerja

Predpogoj: Node.js 20+.

```bash
cd frontend
cp .env.example .env.local    # naslov backend API
npm install
npm run dev                   # http://localhost:3000
npm run lint
```

## Razvojni proces

- Naloge: GitHub Issues, označene z uporabniško zgodbo (npr. `US-03`)
- Napredek: GitHub Project board (To Do / Doing / Done)
- Vsaka sprememba na ločeni veji → Pull Request z `Closes #<issue>`
- Commit sporočila: `feat: ... (#12)`, `fix: ...`, `docs: ...`

## Dokumentacija

Glej mapo [docs/](docs/).
