#!/usr/bin/env bash
# detiene el contenedor docker del proyecto

set -euo pipefail
dos2unix "$0" >/dev/null 2>&1 || true

# colores
BLUE="\e[34m"
GREEN="\e[32m"
BOLD="\e[1m"
RESET="\e[0m"

echo -e "\n${BOLD}${BLUE}[docker] 🛑 Deteniendo contenedor del proyecto...${RESET}\n"
docker compose down
echo -e "\n${GREEN}✔️ [docker] Contenedor detenido correctamente.${RESET}\n"

echo -e "\n${BOLD}${BLUE}✅ Listo.${RESET}\n"
