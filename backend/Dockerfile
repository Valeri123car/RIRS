FROM python:3.12-slim

# uv za hitro in ponovljivo namestitev odvisnosti iz uv.lock
COPY --from=ghcr.io/astral-sh/uv:0.13.6 /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Najprej samo odvisnosti, da Docker predpomni ta sloj, dokler se uv.lock ne spremeni.
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-dev --no-install-project

COPY app ./app

EXPOSE 8989
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8989"]
