#!/bin/bash
# crea la estructura base de carpetas para el proyecto de procesamiento de facturas electrónicas

set -e  # detiene si ocurre un error

# colores
GREEN="\e[32m"
BLUE="\e[34m"
YELLOW="\e[33m"
RED="\e[31m"
BOLD="\e[1m"
RESET="\e[0m"

# manejo de ctrl+c
trap 'echo -e "\n${RED}❌ Operación cancelada por el usuario.${RESET}"; exit 1' INT

echo -e "\n${BOLD}${BLUE}📂 Creando estructura de directorios de datos...${RESET}\n"

# si ya existe data/, preguntar antes de sobrescribir
if [ -d "./data" ]; then
    echo -e "${YELLOW}⚠️  Ya existe la carpeta ./data${RESET}"
    read -p "¿Deseas recrearla (esto puede sobrescribir contenido)? [y/n]: " confirm
    confirm=${confirm,,}  # minúsculas
    if [[ "$confirm" != "y" ]]; then
        echo -e "${YELLOW}↩️  Operación cancelada. No se hicieron cambios.${RESET}\n"
        exit 0
    fi
    echo -e "${YELLOW}🧹 Eliminando carpeta anterior...${RESET}"
    rm -rf ./data
fi

# intenta crear la estructura
if mkdir -p ./data/{raw,interim,processed,external,splits/{train,test}} 2>/dev/null; then
    echo -e "${GREEN}✔️ Estructura creada con éxito.${RESET}\n"
else
    echo -e "${RED}❌ Error al crear las carpetas.${RESET}\n"
    exit 1
fi

# muestra la estructura creada
if command -v tree &> /dev/null; then
    tree ./data
else
    echo -e "${YELLOW}(ℹ️  Comando 'tree' no encontrado, usando 'ls -R')${RESET}\n"
    ls -R ./data
fi

echo -e "\n${BOLD}${BLUE}✅ Listo.${RESET}\n"
