FROM python:3.12-slim

# uv za hitro in ponovljivo namestitev odvisnosti iz uv.lock
COPY --from=ghcr.io/astral-sh/uv:0.13.6 /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# LightGBM (model priporočil, ADR-0006) potrebuje OpenMP knjižnico, ki je slim slika nima.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Najprej samo odvisnosti, da Docker predpomni ta sloj, dokler se uv.lock ne spremeni.
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-dev --no-install-project

COPY alembic.ini ./
COPY alembic ./alembic
COPY app ./app

# Aplikacija ne teče kot root; datoteke ostanejo v lasti roota in so samo za branje.
RUN useradd --system --no-create-home --uid 10001 app
USER app

EXPOSE 8989
# Ob zagonu najprej uveljavi migracije, nato zažene API.
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8989"]
