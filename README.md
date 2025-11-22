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

## 🚀 **Ejecución del pipeline con Makefile**

El proyecto incluye un **pipeline completo y automatizado** para preprocesamiento, separación de datos, rasterización, entrenamiento y OCR usando modelos base o finetuneados.
Todo se ejecuta mediante **`make`**.

### **1. Preprocesamiento inicial**

Antes de entrenar o hacer OCR, prepara los datos:

```bash
make preprocess        # Limpia PDFs, genera hashes
make resolve           # Detecta duplicados
make resolve-apply     # Aplica la resolución de duplicados
make build-train       # Construye el split de entrenamiento (por categorías)
make build-images      # Rasteriza PDFs → PNG (cacheado)
```

### **2. Entrenar modelos TrOCR personalizados (FEL)**

Para ejecutar **todos los fine-tuning** (full page, header y header+augment):

```bash
make ocr-train-all
```

Esto genera tres carpetas de modelos:

* `models/trocr_fel_full_v1/`
* `models/trocr_fel_header_v1/`
* `models/trocr_fel_header_aug_v1/`

Cada una contendrá subcarpetas por *run* con pesos y métricas.

### **3. Generar OCR usando modelo base o fine-tuneado**

#### **Modelo base**

Genera todos los JSON con el modelo original:

```bash
make ocr-all
```

#### **Modelo fine-tuneado**

Header (sin augment):

```bash
make ocr-fel
```

Full page:

```bash
make ocr-fel-full
```

Header + augment:

```bash
make ocr-fel-aug
```

> Cada comando produce archivos JSON dentro de
> `data/interim/ocr_train/<RUN_ID>/<categoria>/*.json`

### **4. Debug visual (crops + texto por región)**

Para inspeccionar qué imágenes y recortes usa el modelo:

```bash
make ocr-debug-all
```

Esto crea carpetas como:

```bash
outputs/debug/base_<timestamp>/
outputs/debug/trocr_fel_header_v1_<timestamp>/
outputs/debug/trocr_fel_full_v1_<timestamp>/
outputs/debug/trocr_fel_header_aug_v1_<timestamp>/
```

Incluyen:

* imágenes de cada región recortada
* PNG de cada página
* textos generados por el modelo por región y por página

### **Flujo completo**

```bash
# Preprocesamiento
make preprocess
make resolve
make resolve-apply
make build-train
make build-images

# Fine-tuning (opcional)
make ocr-train-all

# OCR con cualquier modelo
make ocr-all         # modelo base
make ocr-fel         # header
make ocr-fel-full    # full page
make ocr-fel-aug     # header + augment

# Debug opcional
make ocr-debug-all
```
