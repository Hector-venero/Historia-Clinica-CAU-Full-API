# ===========================================
# 🐍 Flask Backend - Híbrido (Dev / Prod)
# ===========================================

FROM python:3.12-slim

# 🔧 Variables de entorno seguras
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_APP=main.py \
    TZ=America/Argentina/Buenos_Aires

WORKDIR /app

# ===========================================
# 🧱 Dependencias del sistema
# ===========================================
RUN apt-get update && apt-get install -y \
    gcc \
    default-libmysqlclient-dev \
    curl \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# ===========================================
# 📦 Copiar archivos y dependencias
# ===========================================
COPY requirements.txt /app/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir gunicorn

COPY . /app

# ===========================================
# ⏱️ Script de espera para MySQL
# ===========================================
COPY wait-for-it.sh /wait-for-it.sh
RUN chmod +x /wait-for-it.sh

# ===========================================
# 🚀 Comando de ejecución dinámico
# ===========================================
# 👉 Si FLASK_ENV=production -> Gunicorn
# 👉 Si FLASK_ENV=development -> Flask (auto-reload)
CMD ["/bin/bash", "-c", "\
if [ \"$FLASK_ENV\" = 'production' ]; then \
    echo '🚀 Running in PRODUCTION mode (Gunicorn)'; \
    /wait-for-it.sh db:3306 -- gunicorn --workers=3 --timeout=120 --bind=0.0.0.0:5000 main:app; \
else \
    echo '⚙️  Running in DEVELOPMENT mode (Flask)'; \
    /wait-for-it.sh db:3306 -- flask run --host=0.0.0.0; \
fi"]
