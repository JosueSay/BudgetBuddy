# Build Train Split

- **Pipeline anterior:** [04_categorize-data.md](https://github.com/JosueSay/BudgetBuddy/blob/main/docs/guide/04_categorize-data.md)

## Objetivo

Este paso permite **generar el conjunto de entrenamiento (train split)** a partir de las facturas ya categorizadas.
El sistema:

- crea carpetas por cada categoría definida,
- mueve los PDFs a la carpeta correspondiente,
- genera un manifest detallado de archivos,
- produce conteos por categoría,
- registra los archivos omitidos,
- y permite revertir todos los movimientos fácilmente con un comando **undo**.

El resultado será un dataset limpio y organizado, listo para la etapa de modelado (OCR, LayoutLMv3, clasificación, etc.).

## Ejecución del split de entrenamiento

Desde la raíz del proyecto:

```bash
make build-train
```

Internamente ejecuta:

```bash
PYTHONPATH=. python scripts/python/build_train_split.py
```

Este comando:

1. Lee las categorías válidas desde `data/processed/categories_meta.json`.

2. Lee las asignaciones del archivo `data/processed/categories.csv`.

3. Crea carpetas por categoría dentro de:

   ```bash
   data/splits/train/<categoria>/
   ```

4. Mueve cada PDF a su carpeta correspondiente.

5. Registra todos los movimientos en un log de la corrida.

6. Genera varios archivos en `data/processed/`.

## Archivos generados

### 1. Manifest del split

```bash
data/processed/train_manifest.csv
```

Contiene un registro por cada PDF movido:

```csv
pdf_filename,original_pdf_path,new_pdf_path,category,split,updated_at
```

### 2. Conteo por categoría

```bash
data/processed/train_counts.csv
```

Formato:

```csv
category,file_count
```

### 3. Registros omitidos

```bash
data/processed/train_skipped.csv
```

Incluye las razones por las que un archivo no se movió (categoría no encontrada, archivo inexistente, etc.).

### 4. Log de la corrida (para undo)

Cada vez que se ejecuta `make build-train`, se crea un directorio con timestamp:

```bash
data/splits/.trash/run_YYYYmmdd_HHMMSS/
```

Dentro contiene:

- `train_split_log.csv` — movimientos realizados.
- `train_manifest.bak.csv` — backup del manifest previo.
- `train_counts.bak.csv` — backup del conteo previo.
- `train_skipped.bak.csv` — backup de omitidos previos.

Este log permite revertir completamente la operación.

## Estructura resultante

Después de ejecutar `make build-train`, tu dataset quedará organizado así:

```bash
data/
 └── splits/
     └── train/
         ├── alimentacion_restaurantes/
         ├── servicios_seguros/
         ├── transporte/
         ├── salud/
         ├── compras_electronicos/
         ├── ...
```

Cada carpeta contiene únicamente los PDFs correspondientes a su categoría.

## Revertir cambios (Undo)

Si necesitas deshacer un split por ajustes en categorías o en el JSON, usa:

```bash
make undo-train RUN=run_YYYYmmdd_HHMMSS
```

Ejemplo:

```bash
make undo-train RUN=run_20251119_153012
```

Esto restaurará:

- todos los PDFs a su `pdf_path` original,
- los CSV anteriores del manifest, counts y skipped,
- y limpiará las carpetas vacías del split.

## Persistencia y reanudación

El sistema:

- mantiene logs de cada ejecución,
- respalda automáticamente los CSV previos,
- registra todos los movimientos de archivos,
- y permite correr `build-train` múltiples veces mientras desarrollas tu taxonomía o ajustas categorías.

Esto facilita iterar sin riesgo de romper datos.

## Resultado

Al finalizar este paso, se obtiene un **dataset estructurado por categoría**, ubicado en `data/splits/train/`, con metadata completa y listo para:

- OCR
- Extracción de layout
- Clasificación supervisada
- Entrenamiento de modelos multimodales (LayoutLMv3, TrOCR)

Este split constituye la **base de entrenamiento** para todos los modelos posteriores del proyecto.
