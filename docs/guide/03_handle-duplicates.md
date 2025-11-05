# Manejo de data duplicada

- **Pipeline anterior:** [02_preprocess-data.md](https://github.com/JosueSay/BudgetBuddy/blob/main/docs/guide/02_preprocess-data.md)

## Objetivo

Este paso **no detecta duplicados**, sino que **los maneja** una vez que han sido identificados por el pipeline anterior.
Su función es **resolver duplicados manualmente** para limpiar la data, siempre bajo un **criterio definido** (por nombre o por contenido binario).

El proceso es **interactivo y reversible**: permite elegir qué archivo conservar, mueve los duplicados a una carpeta de papelera (`.trash`) y actualiza los manifests.  
También puede revertirse con un comando que restaura todo a su estado original.

## Criterio de duplicación (`--by`)

El script usa el archivo `data/processed/manifest_duplicates.csv` generado por el paso anterior y opera según el parámetro `--by`:

### `--by name`

- Usa la columna `pdf_filename`  
- Detecta PDFs con el mismo nombre en distintos zips  
- Depende del campo `is_name_duplicate == True` en el CSV  

### `--by hash`

- Usa la columna `sha256`  
- Detecta archivos **idénticos en contenido** aunque tengan nombres distintos  
- Depende del campo `is_hash_duplicate == True`  
- Solo funciona si el CSV fue generado con `--hash` durante el `preprocess`

> **Nota:** por defecto el manejo de duplicados utiliza `--by name` para basarse en el nombre de `*.pdf` pero puede modificarse para utilizar el archivo Makefile:
>
> ```bash
> resolve:
>   PYTHONPATH=. python scripts/python/resolve_duplicates.py --by hash
>
> resolve-apply:
>   PYTHONPATH=. python scripts/python/resolve_duplicates.py --by hash --apply
>```

## Comandos principales

Desde la raíz del proyecto:

### 1. Simular resolución (sin cambios)

```bash
make resolve
```

Ejecuta una **simulación interactiva** del proceso.
Permite ver cómo funciona el sistema, listar duplicados y elegir cuál conservar, pero **no mueve ni modifica nada**.

### 2. Aplicar cambios reales

```bash
make resolve-apply
```

Sigue el mismo flujo que el anterior, pero **mueve los duplicados seleccionados a la papelera** y **actualiza los CSV**:

- Crea un directorio:
  `data/interim/.trash/run_<timestamp>/`
- Guarda:

  - Copias de `manifest_pdfs.csv` y `manifest_duplicates.csv`
  - Un log detallado de las acciones (`deletion_log.csv`)
  - Los PDFs movidos

El log contiene las siguientes columnas:

```csv
action,criterion,group_key,kept_pdf,removed_pdf_original_path,
removed_pdf_trash_path,from_zip,year,block,size_bytes
```

Cada fila documenta qué archivo se mantuvo y cuáles se movieron a la papelera.

### 3. Revertir cambios (Ctrl + Z)

```bash
make undo RUN=<run_name>
```

Ejemplo:

```bash
make undo RUN=run_20251105_153012
```

Restaura todos los archivos a su **ruta original exacta** usando el `deletion_log.csv` y **repone los manifests** desde las copias de respaldo.
Después del undo, los CSV (`manifest_pdfs.csv` y `manifest_duplicates.csv`) quedan **exactamente como antes** de haber ejecutado `resolve-apply`.

## Relación con el siguiente paso

Al resolver los duplicados en este pipeline, la data queda limpia y lista para el siguiente pipeline:

- [04_categorize-data.md](https://github.com/JosueSay/BudgetBuddy/blob/main/docs/guide/04_categorize-data.md) → donde se clasifica la data según el tipo de factura o rubro correspondiente.
