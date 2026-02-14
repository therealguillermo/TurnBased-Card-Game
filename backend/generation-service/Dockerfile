FROM python:3.12-slim

# Optional: font for placeholder image text (DejaVu)
RUN apt-get update && apt-get install -y --no-install-recommends fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
COPY stat_generation_rules.txt ./

ENV ASSETS_DIR=/app/assets \
    CATALOG_PATH=/app/data/card-templates.json \
    RULES_PATH=/app/stat_generation_rules.txt

# Volumes for assets and data are mounted at runtime (docker-compose)
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
