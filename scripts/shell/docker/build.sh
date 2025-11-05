#!/usr/bin/env bash
# construye la imagen docker mostrando logs de compilación

set -euo pipefail
dos2unix "$0" >/dev/null 2>&1 || true

# colores
BLUE="\e[34m"
GREEN="\e[32m"
BOLD="\e[1m"
RESET="\e[0m"

echo -e "\n${BOLD}${BLUE}[docker] 🐳 Iniciando build de imagen con logs visibles...${RESET}\n"
docker compose build
echo -e "\n${GREEN}✔️ [docker] Build completado correctamente.${RESET}\n"
