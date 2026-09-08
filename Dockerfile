FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DB_PATH=/data/bot.db

WORKDIR /srv

COPY pyproject.toml README.md ./
COPY app ./app
COPY chat.py ./

RUN pip install --no-cache-dir . && mkdir -p /data

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
