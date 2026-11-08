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

`RIOT_API_MODE=fixtures` uporablja posnete Riot odgovore, zato aplikacija deluje tudi brez ključa.

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

**Testi:** `uv run pytest`. Testi baze se izvedejo samo, če je nastavljen `TEST_DATABASE_URL` (migrirana baza; podatki se po vsakem testu razveljavijo):

```bash
TEST_DATABASE_URL=$DATABASE_URL uv run pytest
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
