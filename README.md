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
```

## Lokalni zagon

Predpogoji: Docker + Docker Compose, (opcijsko) Riot API ključ z [developer.riotgames.com](https://developer.riotgames.com).

```bash
git clone https://github.com/Valeri123car/RIRS.git
cd RIRS
cp .env.example .env        # vpiši RIOT_API_KEY ali nastavi RIOT_API_MODE=fixtures
docker compose up -d --build
docker compose exec api alembic upgrade head
```

- Frontend: http://localhost:3000
- API dokumentacija: http://localhost:8989/docs

`RIOT_API_MODE=fixtures` uporablja posnete Riot odgovore, zato aplikacija deluje tudi brez ključa.

### Backend brez Dockerja

Predpogoj: [uv](https://docs.astral.sh/uv/).

```bash
cd backend
uv sync                                 # namesti odvisnosti
uv run uvicorn app.main:app --reload --port 8989    # API na http://localhost:8989
uv run pytest                           # testi
uv run ruff check .                     # linter
```

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
