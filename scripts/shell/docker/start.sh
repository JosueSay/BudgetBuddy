#!/usr/bin/env bash
# inicia el contenedor docker del proyecto

set -euo pipefail
dos2unix "$0" >/dev/null 2>&1 || true

# colores
BLUE="\e[34m"
GREEN="\e[32m"
BOLD="\e[1m"
RESET="\e[0m"

echo -e "\n${BOLD}${BLUE}[docker] 🚀 Iniciando contenedor del proyecto...${RESET}\n"
docker compose up -d
echo -e "\n${GREEN}✔️ [docker] Contenedor iniciado correctamente.${RESET}\n"

docker compose ps
echo -e "\n${BOLD}${BLUE}✅ Listo.${RESET}\n"
