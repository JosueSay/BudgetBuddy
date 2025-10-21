# Definición de proyecto - Budget Buddy

**Budget Buddy** será un asistente inteligente diseñado para ayudar a las personas a gestionar sus gastos personales de manera fácil y comprensible. Su función principal es recibir información de gastos, como **facturas o recibos**, y organizarlos automáticamente, identificando montos, fechas, tiendas y categorías de gasto.

## Integrantes

- [Josue Say](https://github.com/JosueSay)
- [Javier Chen](https://github.com/JavierC22153)

## Objetivo general

El objetivo es que el usuario pueda **hacer preguntas en lenguaje natural** sobre su historial de gastos, como:

- "¿En qué gasté más este mes?"
- "Muéstrame cuánto gasté en supermercados vs. entretenimiento."
- "Dame un resumen de mis gastos de los últimos tres meses."

Budget Buddy proporcionará **respuestas claras y estructuradas**, ayudando al usuario a entender y controlar sus finanzas personales sin necesidad de ingresar datos manualmente.

## Alcance del proyecto

Budget Buddy trabajará específicamente con:

1. **Facturas y recibos en español**, incluyendo:

   - PDF de facturas estándar SAT.
   - Fotos de facturas físicas de supermercados.
2. **Extracción de información clave**:

   - Montos, fechas, tiendas, productos y categorías de gasto.
   - Moneda quetzal (GTQ) y normalización de valores si se encuentran en formatos diferentes.
3. **Procesamiento de documentos**:

   - OCR mediante TrOCR para texto impreso.
   - Comprensión de layout y relaciones espaciales mediante LayoutLMv3.
   - Estructuración de datos y análisis semántico mediante LLaMA 2.
4. **Respuestas inteligentes**:

   - Consultas en lenguaje natural sobre gastos y categorías.
   - Resúmenes de gastos por período, categoría o tienda.
5. **Orientación educativa**:

   - Experimentos con fine-tuning y prompts de LLaMA 2 para entender cómo los modelos procesan la información.
   - Documentación de aciertos, errores y análisis del comportamiento del modelo.

**Conceptos clave que debe capturar:**

1. Gastos individuales con detalle (tienda, producto, cantidad, precio).
2. Categorías de gasto y resúmenes por categoría.
3. Respuestas en lenguaje natural basadas en datos extraídos de documentos (facturas, recibos).
4. Posibilidad de automatizar y simplificar la gestión de presupuestos personales.
5. Entender y analizar cómo los modelos procesan datos financieros en español para fines educativos.

## Arquitectura técnica

### 1. Entrada de datos

- **Función:** Recibe información sobre gastos en forma de documentos o imágenes de facturas y recibos.
- **Formato esperado:** JPG, PNG, PDF (imagen escaneada).
- **Consideraciones:** La calidad de la imagen afecta directamente la precisión de los pasos posteriores. También los documentos borrosos o con sombras pueden reducir la exactitud de la extracción de información.

### 2. Reconocimiento de texto (OCR / estructuración inicial)

- **Función:** Convierte la información visual en texto digital legible por máquinas.
- **Salida esperada:** Texto plano o estructura preliminar que contenga los campos principales de la factura o recibo.
- **Consideraciones:** Documentos con múltiples bloques de texto o layouts complejos pueden requerir procesamiento adicional para detectar áreas relevantes y mantener la estructura.

### 3. Procesamiento del lenguaje natural (NLP)

- **Función:** Analiza el texto extraído para identificar y organizar información clave:

  - Montos y tipo de moneda.
  - Fechas de emisión o pago.
  - Tiendas, vendedores o proveedores.
  - Productos o servicios.
  - Categorías de gasto (supermercado, transporte, entretenimiento, etc.).
- **Salida esperada:** Datos estructurados en un formato uniforme (por ejemplo JSON) que permita consultas y agregaciones posteriores.
- **Consideraciones:** El análisis debe permitir clasificar, resumir y contextualizar la información para consultas futuras.

### 4. Interacción en lenguaje natural

- **Función:** Permite al usuario consultar sus gastos mediante preguntas en lenguaje natural.
- **Tipos de consultas posibles:**
  - "¿En qué gasté más este mes?"
  - "Muéstrame un resumen de mis gastos en supermercados."
  - "¿Cuánto gasté en total la semana pasada?"
- **Salida esperada:** Respuesta clara y comprensible, presentando totales, categorías y detalles según la consulta.
- **Consideraciones:** El sistema debe ser capaz de interpretar las preguntas del usuario y relacionarlas con los datos estructurados previamente.

## Modelos

### 1. TrOCR (Transformer OCR) en español

- **Descripción**:

  Modelo basado en Transformer para reconocimiento óptico de caracteres (OCR), entrenado específicamente para texto impreso en español. Funciona transformando imágenes en texto plano mediante un encoder de imagen y un decoder de texto.

- **Enlace**: [qantev/trocr-base-spanish](https://huggingface.co/qantev/trocr-base-spanish)

- **Ventajas**:

  - Reconoce texto impreso con alta precisión (CER ~0.073, WER ~0.20).
  - Permite fine-tuning para mejorar resultados en facturas o recibos locales.
  - Flexible y modular: se puede combinar con otros modelos para análisis semántico.

- **Desventajas / limitaciones**:

  - No reconoce texto manuscrito.
  - No comprende la estructura del documento, solo el contenido textual.
  - Puede necesitar un modelo de detección de texto previo si el layout es complejo.

- **Desafíos / consideraciones**:

  - Ajustar la calidad de las imágenes para obtener resultados óptimos.
  - Posible necesidad de crear datasets locales de facturas para fine-tuning.

- **Lo que permite hacer**:

  - Convertir imágenes de facturas en texto digital.
  - Preparar datos para análisis posterior con un LLM para categorización y resumen.

- **Uso en el stack**: Principal, para OCR y preparación de datos textuales.

### 2. Donut (Document Understanding Transformer)

- **Descripción**:

  Modelo que combina visión por computadora y NLP, capaz de entender documentos directamente y generar estructuras de datos como JSON o XML sin un OCR tradicional.

- **Enlace**: [mychen76/invoice-and-receipts_donut_v1](https://huggingface.co/mychen76/invoice-and-receipts_donut_v1)

- **Ventajas**:

  - Extrae directamente datos estructurados de facturas y recibos.
  - Pipeline: OCR + estructuración + NLP en un solo paso.
  - Permite ajustar la salida (JSON/XML) a tus categorías de gasto.

- **Desventajas / limitaciones**:

  - Experimental: requiere GPU potente para fine-tuning.
  - Modificar la forma de procesar el texto dentro del JSON puede ser menos trivial que con TrOCR.

- **Desafíos / consideraciones**:

  - Necesita dataset local para obtener resultados óptimos en español.
  - Fine-tuning más complejo que modelos separados de OCR y NLP.

- **Lo que permite hacer**:

  - Convertir directamente la factura en datos estructurados listos para análisis.
  - Reducir la pipeline y pasos intermedios.

- **Uso en el stack**: Secundario, útil para pruebas o comparación, pero no el foco principal.

### 3. LayoutLMv3 (OCR + comprensión de layout)

- **Descripción**:

  Modelo que combina visión y NLP para comprender la disposición y relación espacial del texto en documentos, lo que mejora la extracción de campos y relaciones complejas.

- **Enlace**: [jinhybr/OCR-LayoutLMv3-Invoice](https://huggingface.co/jinhybr/OCR-LayoutLMv3-Invoice)

- **Ventajas**:

  - Útil para documentos con estructuras complejas y tablas.
  - Alto desempeño: F1 ~0.87, Accuracy ~0.92.
  - Permite fine-tuning para extraer campos específicos como tienda, monto, fecha.

- **Desventajas / limitaciones**:

  - Pipeline más pesada que Donut para obtener la data en un JSON simple.
  - Requiere mayor cantidad de datos para fine-tuning efectivo.

- **Desafíos / consideraciones**:

  - Preparar datasets locales con layouts variados de facturas.
  - Ajustar estrategias de entrenamiento (congelar capas, learning rate, etc.) para optimizar resultados.

- **Lo que permite hacer**:

  - Analizar y modificar cómo se interpreta la estructura del documento.
  - Extraer información precisa para documentos complejos y luego pasarlos a un LLM para consultas.

- **Uso en el stack**: Principal, para entender layout y relaciones espaciales en documentos complejos.

### 4. LLaMA 2 – 7B (LLM para análisis y razonamiento de facturas)

- **Descripción**:

  Modelo de lenguaje grande (LLM) basado en Transformer decoder-only, entrenado por Meta AI, con pesos abiertos y posibilidad de fine-tuning educativo. Se usará para interpretar los textos y datos extraídos de los documentos OCR, generando resúmenes, categorizaciones o respuestas a consultas en español.

- **Enlace**: [LLaMA 2 – 7B](https://huggingface.co/meta-llama/Llama-2-7b-hf)

- **Ventajas**:

  - Licencia abierta y gratuita para uso educativo.
  - Compatible con fine-tuning mediante LoRA, QLoRA y PEFT.
  - Procesa texto en español y entiende contexto financiero con entrenamiento local.

- **Desventajas / limitaciones**:

  - Multilingüe, pero español no nativo: puede requerir adaptación.
  - Requiere GPU moderada (8–12 GB VRAM para 4-bit quantization).

- **Desafíos / consideraciones**:

  - Preparar dataset con textos extraídos por OCR y layouts.
  - Experimentar con prompts y fine-tuning para entender cómo responde a datos financieros.
  - Documentar aciertos y errores para análisis educativo.

- **Lo que permite hacer**:

  - Tomar los datos extraídos por OCR/LayoutLMv3 y analizarlos semánticamente.
  - Generar resúmenes por categoría, tienda o fecha.
  - Servir como el “cerebro” del sistema de análisis de facturas.

- **Uso en el stack**: Principal.

## Documentación, investigación y conceptos por aplicar (actualizado)

### 1. OCR y reconocimiento de texto

- **Conceptos clave:**

  - Reconocimiento óptico de caracteres (OCR).
  - Diferencia entre OCR tradicional y modelos basados en Transformer (TrOCR).
  - Preprocesamiento de imágenes para OCR: resolución, contraste, limpieza de ruido, rotación y recorte para fotos de facturas físicas.
  - Evaluación de precisión: CER (Character Error Rate), WER (Word Error Rate).

- **Tareas de investigación / a aplicar:**

  - Comparar desempeño de OCR tradicional vs TrOCR para facturas PDF y fotos de supermercados.
  - Preparar datasets locales en español con facturas SAT y recibos físicos para **fine-tuning**.
  - Técnicas de detección de texto para documentos con layouts complejos.

### 2. Procesamiento de documentos estructurados

- **Conceptos clave:**

  - Extracción de campos y relaciones espaciales con LayoutLMv3.
  - Transformación de documentos a estructuras JSON uniformes.
  - Normalización de datos: fechas, montos, moneda quetzal (GTQ), cantidades.

- **Tareas de investigación / a aplicar:**

  - Diseñar esquema de datos uniforme para todos los recibos/facturas.
  - Identificar categorías y subcategorías de gasto relevantes para Guatemala.
  - Validar que los montos y totales sean consistentes con los ítems extraídos.

### 3. Procesamiento de lenguaje natural (LLM)

- **Conceptos clave:**

  - Clasificación de texto: tiendas, productos, categorías de gasto.
  - Resumen de información: totales, subtotales, reportes por periodo.
  - Modelos LLM en español: LLaMA 2 (principal), BLOOMZ o HunyuanImage-3 (uso secundario, educativo).
  - Prompts y técnicas de prompt engineering para consultas en lenguaje natural.

- **Tareas de investigación / a aplicar:**

  - Ajustar LLaMA 2 para responder preguntas sobre gastos usando datos extraídos.
  - Evaluar desempeño del LLM en español y contexto financiero local.
  - Integrar la salida de TrOCR o LayoutLMv3 con LLM para análisis contextual y resúmenes financieros.

### 4. Arquitectura de pipelines y unificación de modelos

- **Conceptos clave:**

  - Modularidad vs modelos unificados.
  - Pipeline de procesamiento: imagen → OCR (TrOCR) / Document Understanding (LayoutLMv3) → datos estructurados → LLM (LLaMA 2).
  - Fine-tuning conjunto: cómo ajustar OCR + LLM para mejorar precisión en facturas locales.
  - Estrategias de eficiencia: congelar capas, usar modelos base más pequeños, inferencia optimizada.

- **Tareas de investigación / a aplicar:**

  - Diseñar arquitectura flexible que permita reemplazar o mejorar modelos sin romper la pipeline.
  - Explorar técnicas de fine-tuning y tuning combinando OCR y LLM para entender cómo procesan los datos, no solo obtener resultados correctos.

### 5. Gestión de datos y análisis financiero personal

- **Conceptos clave:**

  - Estructura de información financiera: ingresos, gastos, categorías, fechas.
  - Análisis temporal de gastos: mensual, semanal, anual.
  - Visualización de datos: tablas, gráficos, dashboards.
  - Validación y control de consistencia de información.

- **Tareas de investigación / a aplicar:**

  - Definir categorías y subcategorías de gasto según contexto local (Guatemala).
  - Crear reportes automáticos de gasto total, gasto por categoría, comparativos entre meses.
  - Integrar la salida del pipeline con base de datos local o estructuras para consultas posteriores.
