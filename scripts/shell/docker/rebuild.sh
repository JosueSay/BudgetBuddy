#!/usr/bin/env bash
# rebuild (sin cache) y arranque del proyecto docker

set -euo pipefail
dos2unix "$0" >/dev/null 2>&1 || true

# colores
BLUE="\e[34m"
GREEN="\e[32m"
BOLD="\e[1m"
RESET="\e[0m"

echo -e "\n${BOLD}${BLUE}[docker] 🔄 Rebuild de imagen (sin cache) y arranque del proyecto...${RESET}\n"
docker compose build --no-cache
docker compose up -d --remove-orphans
echo -e "\n${GREEN}✔️ [docker] Contenedores levantados correctamente.${RESET}\n"

docker compose ps
echo -e "\n${BOLD}${BLUE}✅ Listo.${RESET}\n"
