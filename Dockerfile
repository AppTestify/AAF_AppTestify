# syntax=docker/dockerfile:1
FROM python:3.11-slim AS builder
WORKDIR /build
RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.11-slim AS runtime
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libpq5 && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10001 appuser
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY aaf/ aaf/
COPY agents/ agents/
COPY app/ app/
COPY connectors/ connectors/
COPY fixtures/ fixtures/
COPY orchestrator/ orchestrator/
COPY llm/ llm/
COPY metrics/ metrics/
COPY pm_interface/ pm_interface/
COPY tools/ tools/
COPY scripts/ scripts/
COPY alembic/ alembic/
COPY alembic.ini .
RUN mkdir -p /app/data && chown -R appuser:appuser /app
USER appuser
ENV PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
