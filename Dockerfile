# ==============================================================================
# SmartMyOdoo — Dockerfile (DOCKER-01 / T3)
# Multi-stage: builder (kompiluje ciężkie deps ML) -> runtime (slim, non-root).
# Decyzje sprintu:
#   D1: base = python:3.12-slim (pewne wheels: presidio/spaCy/numpy/cryptography).
#   D2: VAULT_DIR ENV-owany (stan vaultu na /data/vault, wolumen).
#   D4: host 0.0.0.0 w kontenerze (ekspozycję kontroluje mapowanie portów hosta).
#   D6: vault tworzony first-run przez UI (POST /api/init), NIE przez ENV.
# ADR-008: ZERO sekretów w obrazie (patrz .dockerignore). Stan tylko na wolumenach.
# ==============================================================================

# ------------------------------------------------------------------------------
# Stage 1: builder — instaluje zależności (w tym kompilowane) do izolowanego prefixu.
# ------------------------------------------------------------------------------
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Toolchain do budowy wheels, których nie ma w wersji binarnej dla 3.12-slim.
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        g++ \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Najpierw tylko manifest zależności — lepszy cache warstw (kod zmienia się częściej).
COPY requirements.txt constraints.txt requirements-rag.txt ./

# --pre: dopuszcza prerelease (markitdown[all] ciąga azure-* w wersjach beta — nota
#   venv-qa-gaps). UWAGA: sprint pisał `--prerelease=allow`, ale to flaga `uv`, nie `pip`
#   — odpowiednik pip to `--pre` (zweryfikowane buildem: pip odrzuca `--prerelease`).
# -c constraints.txt: pinuje stos ML (numpy/spacy/thinc) do STABILNYCH wersji, bo
#   samo --pre wciągało numpy 2.5rc/spacy 4.0.dev (ABI crash spacy.load w runtime).
# Instalujemy do /install (prefix), żeby skopiować tylko site-packages do runtime.
# pl_core_news_md jest w requirements.txt jako release wheel (PL model dla PII middleware).
RUN pip install --prefix=/install --pre -c constraints.txt -r requirements.txt

# RAG-DOCKER-01: wektorowy RAG (LanceDB + sentence-transformers + torch CPU-only).
# Osobne polecenie BEZ --pre (by nie wciągać prerelease torcha), z constraints (numpy
# pinned spójnie). torch CPU z indeksu PyTorch (--extra-index-url w requirements-rag.txt)
# — local-version „+cpu" ma pierwszeństwo nad CUDA z PyPI, więc bez ~2GB CUDA.
RUN pip install --prefix=/install -c constraints.txt -r requirements-rag.txt

# ------------------------------------------------------------------------------
# Stage 2: runtime — slim, bez toolchainu, non-root.
# ------------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    # D2: domyślny katalog vaultu = /data/vault (wolumen). Compose i tak nadpisze.
    VAULT_DIR=/data/vault \
    # D2/persystencja: DB w /data (wolumen). Compose nadpisze pełnym URL-em.
    DATABASE_URL=sqlite:////data/smartmyodoo.db

# curl — potrzebny do HEALTHCHECK uderzającego w /api/status.
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Zależności zbudowane w builderze (site-packages + entry-pointy/binarki, np. uvicorn).
COPY --from=builder /install /usr/local

WORKDIR /app

# Kod aplikacji (sekrety/vault/DB wykluczone przez .dockerignore).
COPY smartmyodoo ./smartmyodoo
COPY pyproject.toml requirements.txt ./
# RAG-DOCKER-01: źródła wiedzy do zasiania bazy wektorowej (dziś NIE kopiowane).
COPY knowledge ./knowledge

# RAG-DOCKER-01: baza wektorowa + model embeddingów (ONNX) ZASZYTE W OBRAZIE
# (offline-ready), żeby każdy `docker compose up` miał działający Shared Brain bez
# pobierania w runtime.
#   SMARTMYODOO_LANCEDB_PATH=/app/.lancedb — baza w obrazie (NIE na wolumenie /data; to
#     wspólna treść statyczna, nie stan usera).
#   FASTEMBED_CACHE=/app/.fastembed — cache modelu ONNX czytelny dla appuser (download robi root).
ENV SMARTMYODOO_LANCEDB_PATH=/app/.lancedb \
    FASTEMBED_CACHE=/app/.fastembed
# Seed konstruuje LanceDBClient → pobiera model ONNX (fastembed) do FASTEMBED_CACHE i embeduje
# dokumenty knowledge/ do /app/.lancedb. Jeden krok = model + baza zaszyte w obrazie.
RUN python -m smartmyodoo.swarm.brain.seed_knowledge knowledge

# Non-root user (ADR-008 / Sekcja D). /data tworzony i przejmowany na własność,
# by first-run init vaultu (POST /api/init) mógł pisać do /data/vault. chown -R /app
# obejmuje też zaszytą bazę RAG (/app/.lancedb) i cache modelu (/app/.hfcache).
RUN useradd --create-home --uid 1001 appuser \
    && mkdir -p /data/vault /data/logs \
    && chown -R appuser:appuser /app /data

USER appuser

EXPOSE 8000

# Healthcheck: /api/status zwraca 200 + {"initialized": bool} (auth.py:57).
# start-period dłuższy — pierwszy start ładuje model spaCy/presidio (cięższe).
HEALTHCHECK --interval=15s --timeout=5s --start-period=40s --retries=5 \
    CMD curl -fsS http://127.0.0.1:8000/api/status || exit 1

# Entrypoint = uvicorn (brak subkomendy `serve` — patrz fakty sprintu). Host 0.0.0.0 (D4).
CMD ["python", "-m", "uvicorn", "smartmyodoo.api:app", "--host", "0.0.0.0", "--port", "8000"]
