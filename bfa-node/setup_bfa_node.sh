#!/bin/bash
set -e

# ================================
# 🚀 Setup del nodo BFA local
# ================================

# Colores
GREEN="\033[1;32m"
YELLOW="\033[1;33m"
RED="\033[1;31m"
NC="\033[0m"

echo -e "${GREEN}🚀 Iniciando configuración del nodo BFA local...${NC}"

# 1️⃣ Instalar dependencias básicas
apt-get update -y && apt-get install -y git curl build-essential software-properties-common

# 2️⃣ Instalar Go si no está
if ! command -v go &> /dev/null; then
  echo -e "${YELLOW}🔧 Instalando Go...${NC}"
  add-apt-repository -y ppa:longsleep/golang-backports
  apt-get update -y && apt-get install -y golang-go
fi

# 3️⃣ Clonar y compilar Geth si no existe
if [ ! -f "/usr/local/bin/geth" ]; then
  echo -e "${YELLOW}📦 Clonando y compilando go-ethereum...${NC}"
  cd /nucleo
  if [ ! -d "go-ethereum" ]; then
    git clone https://github.com/ethereum/go-ethereum.git
  fi
  cd go-ethereum
  make geth
  cp build/bin/geth /usr/local/bin/
fi

# 4️⃣ Verificar existencia de genesis.json
if [ ! -f "/nucleo/test2network/genesis.json" ]; then
  echo -e "${RED}❌ ERROR: No se encontró /nucleo/test2network/genesis.json${NC}"
  echo -e "${RED}👉 Asegurate de montarlo correctamente desde el host.${NC}"
  exit 1
fi

# 5️⃣ Inicializar la red (solo si no existe)
if [ ! -d "/nucleo/test2network/geth" ]; then
  echo -e "${GREEN}🧱 Inicializando red con genesis.json...${NC}"
  geth --datadir /nucleo/test2network init /nucleo/test2network/genesis.json
fi

# 6️⃣ Verificar keystore
if [ ! -d "/nucleo/test2network/keystore" ]; then
  echo -e "${RED}⚠️ No se encontró el directorio keystore en /nucleo/test2network${NC}"
  echo -e "${YELLOW}📁 Crealo y copiá tu archivo UTC--...--9597A10a33Cf9a30A46Eb01E63Ab1488B25505A3${NC}"
  mkdir -p /nucleo/test2network/keystore
fi

# 7️⃣ Desbloquear cuenta y lanzar nodo
echo -e "${GREEN}🔓 Desbloqueando cuenta 0x9597A10a33Cf9a30A46Eb01E63Ab1488B25505A3...${NC}"

exec geth --datadir /nucleo/test2network \
  --networkid 99118822 \
  --http --http.addr 0.0.0.0 --http.port 8545 \
  --http.api eth,net,web3,txpool \
  --http.corsdomain="*" --http.vhosts="*" \
  --unlock "0x9597A10a33Cf9a30A46Eb01E63Ab1488B25505A3" \
  --password <(echo "2908") \
  --verbosity 3