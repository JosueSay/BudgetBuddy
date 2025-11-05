# Categorización de datos

- **Pipeline anterior:** [03_handle-duplicates.md](03_handle-duplicates.md)

## Objetivo

Este paso permite **clasificar y organizar manualmente las facturas PDF (FEL)** según su tipo o rubro, utilizando una interfaz web local.
El sistema facilita crear categorías y subcategorías personalizadas, visualizar los documentos y mantener un registro persistente de las asignaciones.

La información generada en este proceso se guardará en la carpeta `data/processed/` para ser utilizada en las siguientes etapas del proyecto.

## Ejecución del servidor web

Desde la raíz del proyecto:

```bash
make web
```

Esto iniciará un servidor local accesible en el navegador en:

```bash
http://localhost:8000/
```

Al ingresar, se abrirá la aplicación **BudgetBuddy – Categorizador de PDFs**, donde podrás gestionar categorías y clasificar los documentos.

## Funcionalidades principales

### 1. Creación y gestión de categorías

Desde la parte superior de la página:

- Crear nuevas categorías y subcategorías (por ejemplo: `alimentación_restaurantes`, `transporte_gasolina`).
- Renombrar o eliminar categorías existentes.
- Las categorías se guardan en el archivo:

  ```bash
  data/processed/categories_meta.json
  ```

### 2. Categorización de facturas

En la tabla principal podrás:

- Buscar y filtrar facturas (`todos`, `sin categoría`, `clasificados`).
- Ver la información básica de cada PDF (nombre, origen, año, bloque).
- Asignar o cambiar su categoría.
- Visualizar el documento directamente en el navegador.
- Marcar automáticamente los que no están disponibles (si el archivo no existe en el host).

Las asignaciones se registran en el archivo:

```bash
data/processed/categories.csv
```

El CSV incluye:

```csv
pdf_path,pdf_filename,category,updated_at,missing
```

## Persistencia y reanudación

El sistema guarda automáticamente el progreso.
Si el servidor se detiene y se vuelve a iniciar, las categorías y asignaciones previas se restauran desde los archivos de `data/processed/`.

Esto permite continuar la categorización en distintas sesiones sin perder información.

## Resultado

Al finalizar este paso, se obtiene una **base de facturas categorizadas** que servirá como entrada para los siguientes procesos de análisis y modelado.

Este conjunto estructurado será la base para la **etapa de aprendizaje automático**, donde los modelos podrán aprender a identificar o clasificar facturas según su categoría.
