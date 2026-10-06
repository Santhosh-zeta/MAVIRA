FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app

ARG INSTALL_LLM=false
COPY requirements.txt requirements-dev.txt requirements-llm.txt ./
RUN pip install -r requirements-dev.txt && if [ "$INSTALL_LLM" = "true" ]; then pip install -r requirements-llm.txt; fi

COPY . .
RUN useradd --create-home --uid 10001 mavira && mkdir -p /data/storage && chown -R mavira /data /app
USER mavira

ENV STORAGE_DIR=/data/storage
EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers"]
