FROM node:22-bookworm-slim AS frontend
WORKDIR /src/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/src/ ./src/
COPY frontend/index.html frontend/vite.config.ts frontend/tsconfig*.json frontend/postcss.config.js frontend/tailwind.config.js ./
RUN npm run build

FROM python:3.12-slim-bookworm AS runtime
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PORT=8080 HOST=0.0.0.0 STATIC_DIR=/app/frontend/dist
WORKDIR /app/backend
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt \
    && useradd --uid 10001 --create-home storyparity
COPY --chown=storyparity:storyparity backend/app/ ./app/
COPY --from=frontend --chown=storyparity:storyparity /src/frontend/dist /app/frontend/dist
USER storyparity
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/api/health', timeout=4)"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1"]
