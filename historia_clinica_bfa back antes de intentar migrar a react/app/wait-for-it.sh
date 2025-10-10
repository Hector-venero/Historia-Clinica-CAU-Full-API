#!/usr/bin/env bash
set -e

host="$1"
shift
cmd="$@"

echo "⏳ Esperando que $host esté disponible..."

while ! nc -z ${host%:*} ${host#*:}; do
  sleep 1
done

echo "✅ $host está disponible. Arrancando app..."
exec $cmd
