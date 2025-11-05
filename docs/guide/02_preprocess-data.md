# Pre-procesamiento de data

**Pipelines anteriores:**  

- [00_environment-setup.md](https://github.com/JosueSay/BudgetBuddy/blob/main/docs/guide/00_environment-setup.md)  
- [01_download-fel-data.md](https://github.com/JosueSay/BudgetBuddy/blob/main/docs/guide/01_download-fel-data.md)

## Objetivo

Este módulo prepara los datos descargados en el paso anterior.  
Su función es **descomprimir todos los archivos ZIP**, listar todos los **PDFs disponibles**, y generar un **inventario (manifest)** con su información básica.  
Además, detecta posibles **duplicados** tanto por **nombre de archivo** como por **contenido binario (hash)**.

El objetivo principal es tener una visión completa del conjunto de PDFs y poder identificar qué archivos deben ser revisados antes de pasar al siguiente pipeline de manejo de duplicados.

## Qué hace el pipeline

1. **Descomprime** todos los archivos `.zip` ubicados en `data/raw/` dentro de `data/interim/unzipped/`.
2. **Escanea todos los PDFs** extraídos y construye un archivo `manifest_pdfs.csv` con información como:
   - nombre del archivo (`pdf_filename`)
   - origen (`zip_root`, `year`, `block`)
   - ruta (`pdf_path`)
   - tamaño en bytes
3. **Detecta duplicados** de dos formas:
   - **Por nombre:** archivos con el mismo nombre en diferentes ZIPs.  
   - **Por hash:** archivos idénticos en contenido, sin importar su nombre.
4. **Genera dos salidas:**
   - `data/processed/manifest_pdfs.csv` → inventario completo de PDFs.  
   - `data/processed/manifest_duplicates.csv` → listado de duplicados detectados.

## Cómo ejecutarlo

Desde la raíz del proyecto:

```bash
make preprocess
```

## Banderas disponibles

Estas banderas se pueden modificar en el archivo `Makefile`.

### `--hash`

- Calcula el **SHA-256** de cada PDF para identificar duplicados por contenido.
- Si no se usa, solo se detectan duplicados por nombre.
- Es más lento, pero más preciso.

### `--overwrite`

- Permite **reemplazar** los archivos CSV existentes (`manifest_pdfs.csv` y `manifest_duplicates.csv`).
- Si se omite, el script detiene la ejecución si los archivos ya existen.

## Relación con el siguiente paso

Los archivos `manifest_pdfs.csv` y `manifest_duplicates.csv` generados aquí son **la base** para el siguiente pipeline:

- [03_handle-duplicate.md](https://github.com/JosueSay/BudgetBuddy/blob/main/docs/guide/03_handle-duplicates.md), donde se gestionan manualmente los duplicados detectados.
