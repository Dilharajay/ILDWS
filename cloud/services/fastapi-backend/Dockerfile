# ---- Build stage ----
FROM python:3.11-slim AS builder

WORKDIR /build
COPY pyproject.toml ./
RUN pip install --no-cache-dir --prefix=/install .

# ---- Runtime stage ----
FROM python:3.11-slim

RUN groupadd -r ilews && useradd -r -g ilews -d /app -s /sbin/nologin ilews

WORKDIR /app
COPY --from=builder /install /usr/local
COPY . .

RUN chown -R ilews:ilews /app
USER ilews

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
