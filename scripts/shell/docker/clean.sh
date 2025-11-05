#!/usr/bin/env bash
# elimina solo el contenedor e imagen locales de este proyecto docker

set -euo pipefail
dos2unix "$0" >/dev/null 2>&1 || true

# colores
BLUE="\e[34m"
GREEN="\e[32m"
BOLD="\e[1m"
RESET="\e[0m"

echo -e "\n${BOLD}${BLUE}[docker] 🧹 Eliminando contenedor e imagen locales del proyecto...${RESET}\n"
docker compose down --rmi local --volumes --remove-orphans
echo -e "\n${GREEN}✔️ [docker] Recursos eliminados correctamente.${RESET}\n"
