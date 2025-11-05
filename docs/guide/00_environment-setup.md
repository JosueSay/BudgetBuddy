# Preparación de entorno

## Requisitos previos

Este proyecto utiliza **Docker** para ejecutar su entorno de desarrollo.  
Fue probado en **Ubuntu 22.04** (nativo o mediante **WSL2**), aunque puede funcionar en otras distribuciones compatibles.

### Requisitos básicos

- **Docker** → versión recomendada: `28.3.0` (build `38b7060`) o superior  
- **dos2unix** → necesario para limpiar y ejecutar correctamente los scripts `.sh` desde el host  

Instala `dos2unix` ejecutando:

```bash
sudo apt-get update && sudo apt-get install -y dos2unix
```

## Preparación de scripts

Antes de ejecutar cualquier script `.sh`, asegúrate de normalizar los finales de línea y otorgar permisos de ejecución.

Desde la raíz del proyecto, ejecuta:

```bash
find scripts/shell -type f -name "*.sh" -exec dos2unix {} \; -exec chmod +x {} \;
find scripts/shell -type f -name "*.sh" -exec ls -l {} \;
```

Estos comandos:

- Convierten todos los scripts al formato Unix (`LF`)
- Otorgan permisos de ejecución a cada uno
- Muestran la lista con los permisos aplicados

## Configuración inicial de directorios de datos

Antes de levantar el contenedor, ejecuta el script que crea la estructura base para almacenar los datos del proyecto:

```bash
./scripts/shell/init/01_setup-data-dirs.sh
```

Este script genera las carpetas necesarias dentro de `data/`, asegurando que el pipeline tenga las rutas esperadas antes de procesar archivos.

Solo necesitas ejecutarlo una vez al iniciar el proyecto o cuando se eliminen las carpetas de datos o se reinicie el pipeline global.

## Ejecución del entorno Docker

Una vez preparados los scripts, puedes usar los siguientes comandos:

```bash
# Construir imagen
./scripts/shell/docker/build.sh

# Iniciar contenedor
./scripts/shell/docker/start.sh

# Detener contenedor
./scripts/shell/docker/stop.sh

# Reiniciar contenedor
./scripts/shell/docker/restart.sh

# Reconstruir imagen y reiniciar
./scripts/shell/docker/rebuild.sh

# Limpiar (contenedor/imagen/volúmenes de este proyecto)
./scripts/shell/docker/clean.sh

# Entrar a la terminal del contenedor
docker exec -it budgetbuddy bash
```

En caso de no poder ejecutar los `.sh`, se pueden usar directamente los comandos de Docker Compose:

```bash
# Construir
docker compose build

# Iniciar en segundo plano
docker compose up -d

# Entrar a la terminal del contenedor
docker exec -it budgetbuddy bash

# Detener
docker compose down

# Reconstruir sin caché y subir
docker compose build --no-cache && docker compose up -d --remove-orphans

# Limpiar dedicado a este proyecto
docker compose down --rmi local --volumes --remove-orphans
```

Para salir de la sesión interactiva dentro del contenedor, presiona `CTRL + D` y ejecutar los `.sh` o comandos de docker.

## Continuar con la guía

Una vez configurado e iniciado el entorno Docker correctamente, continúa con los siguientes módulos segun las guías en [docs/guide/*.md](https://github.com/JosueSay/BudgetBuddy/tree/main/docs/guide)
