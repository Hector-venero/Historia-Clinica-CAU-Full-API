#!/bin/bash
set -e

# Migraciones antes de levantar la app. Con set -e, si fallan el contenedor no
# arranca: es preferible a servir la app contra un esquema desactualizado.
if [ "$MULTI_TENANT" = "true" ]; then
  # Plataforma: el plano de control primero (de ahi sale la lista de
  # consultorios) y despues la base de cada uno.
  echo "🗄️  Aplicando migraciones (plataforma y consultorios)..."
  python /app/migrate.py --todos
else
  echo "🗄️  Aplicando migraciones pendientes..."
  python /app/migrate.py
fi

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
