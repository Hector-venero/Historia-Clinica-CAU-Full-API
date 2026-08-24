#!/bin/bash
set -e

# Migraciones antes de levantar la app. Con set -e, si fallan el contenedor no
# arranca: es preferible a servir la app contra un esquema desactualizado.
echo "🗄️  Aplicando migraciones pendientes..."
python /app/migrate.py

if [ "$FLASK_ENV" = "production" ]; then
  echo "🚀 Running in PRODUCTION mode (Gunicorn)"
  exec gunicorn \
    --chdir / \
    --pythonpath /app \
    --workers=3 \
    --timeout=120 \
    --bind=0.0.0.0:5000 \
    app.main:app
else
  echo "⚙️ Running in DEVELOPMENT mode (Flask)"
  exec flask run --host=0.0.0.0
fi
