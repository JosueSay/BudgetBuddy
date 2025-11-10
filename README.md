# 🧾 BudgetBuddy

**BudgetBuddy** es un proyecto orientado a la **automatización, procesamiento y análisis de facturas electrónicas (FEL)** de la **SAT Guatemala**, con el objetivo de construir un pipeline reproducible que permita organizar, limpiar y clasificar los datos de manera estructurada.

El desarrollo se realiza principalmente en **Python 3.12.3**, dentro de un entorno **Dockerizado** para mantener la portabilidad y consistencia entre entornos.

## 📚 Guías y documentación

El flujo de trabajo del proyecto está documentado paso a paso en los archivos dentro de:

➡️ [docs/guide/*.md](https://github.com/JosueSay/BudgetBuddy/tree/main/docs/guide)

Estas guías explican desde la configuración del entorno, descarga y preprocesamiento de datos, hasta la detección de duplicados y clasificación.

## ⚙️ Requisitos previos

El proyecto fue configurado y probado en:

* **Ubuntu 22.04 / WSL2**
* **Docker** versión recomendada: `28.3.0` (build `38b7060`)
* **dos2unix** (para normalizar scripts `.sh`)

Instalación básica:

```bash
sudo apt-get update && sudo apt-get install -y dos2unix
```

## 🧰 Preparación de scripts

Convierte los scripts de Docker a formato Unix y hazlos ejecutables:

```bash
dos2unix scripts/shell/docker/*.sh
chmod +x scripts/shell/docker/*.sh
```

## 🗂️ Configuración inicial de directorios de datos

Ejecuta el script de inicialización para crear la estructura base de datos:

```bash
./scripts/shell/init/01_setup-data-dirs.sh
```

## 🐳 Ejecución del entorno Docker

Scripts principales para gestionar el entorno:

```bash
./scripts/shell/docker/build.sh     # Construir la imagen
./scripts/shell/docker/start.sh     # Iniciar el contenedor
./scripts/shell/docker/stop.sh      # Detener el contenedor
./scripts/shell/docker/restart.sh   # Reiniciar el contenedor
./scripts/shell/docker/rebuild.sh   # Reconstruir imagen y reiniciar
./scripts/shell/docker/clean.sh     # Eliminar solo este contenedor
```

> 🚧 **Nota:** El proyecto se encuentra en fase inicial de desarrollo.
> A medida que avance, se documentarán los resultados, modelos y procesos detallados en las guías correspondientes.
