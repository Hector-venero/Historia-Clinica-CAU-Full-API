#!/bin/bash
# Script de prueba para las rutas de usuarios (Flask API)
# Usa curl con cookies para mantener sesión

API="http://localhost:5000/api"
USER="admin"
PASS="admin123"
COOKIES="cookies.txt"

echo "🔹 1) Login..."
curl -s -c $COOKIES -H "Content-Type: application/json" \
  -X POST $API/login \
  -d "{\"username\":\"$USER\",\"password\":\"$PASS\"}" | jq

echo -e "\n🔹 2) Listar usuarios activos..."
curl -s -b $COOKIES $API/usuarios | jq

echo -e "\n🔹 3) Soft delete del usuario con ID=3..."
curl -s -b $COOKIES -X DELETE $API/usuarios/3 | jq

echo -e "\n🔹 4) Listar usuarios activos (ya no debería estar el ID=3)..."
curl -s -b $COOKIES $API/usuarios | jq

echo -e "\n🔹 5) Listar todos incluyendo inactivos (ID=3 debería estar, activo=0)..."
curl -s -b $COOKIES "$API/usuarios?inactivos=1" | jq

echo -e "\n🔹 6) Reactivar usuario ID=3..."
curl -s -b $COOKIES -X PUT $API/usuarios/3/activar | jq

echo -e "\n🔹 7) Listar usuarios activos (ID=3 debería volver a aparecer)..."
curl -s -b $COOKIES $API/usuarios | jq
