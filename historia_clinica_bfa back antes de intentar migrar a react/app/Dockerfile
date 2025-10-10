# app/Dockerfile

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_APP=main.py \
    FLASK_RUN_HOST=0.0.0.0 \
    FLASK_RUN_PORT=5000

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    netcat-openbsd \
    default-libmysqlclient-dev \
    && rm -rf /var/lib/apt/lists/*

COPY . /app

# 🔥 Aseguramos permisos de ejecución al script
COPY wait-for-it.sh /wait-for-it.sh
RUN chmod +x /wait-for-it.sh

RUN pip install --upgrade pip && pip install -r requirements.txt

# ✅ Nuevo CMD con wait
CMD ["/wait-for-it.sh", "db:3306", "--", "flask", "run"]
