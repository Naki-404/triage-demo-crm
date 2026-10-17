# Qazaq CRM: API + built frontend in one image (build context: repository root).
FROM node:22-alpine@sha256:0a7108bf6c7bf5de370ffb1a3ed6be93d405b43ff159f681a8d18c0e2bc2e402 AS frontend
WORKDIR /ui
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend .
RUN npm run build

FROM python:3.12-slim@sha256:05cda9777409a9c3ffddd94a4c476b79f0769a0b4857f0c7ed9226b6800b0d6f
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY backend/requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt && useradd --create-home --uid 10002 crm
COPY backend /app
COPY --from=frontend /ui/dist /app/static
RUN rm -rf /app/tests /app/logs && mkdir -p /app/exports /app/logs && chown -R crm:crm /app/exports /app/logs
USER crm
# Safe by default: lab/stand deployments must opt out explicitly (ENVIRONMENT=development + own secrets).
ENV STATIC_DIR=/app/static ENVIRONMENT=production STAND_CONTROL_ENABLED=false FORWARDED_ALLOW_IPS=127.0.0.1
EXPOSE 9000
HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:9000/health')"
CMD ["sh", "-c", "python -m alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 9000 --proxy-headers --forwarded-allow-ips=\"$FORWARDED_ALLOW_IPS\""]
