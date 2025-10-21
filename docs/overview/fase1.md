# Resumen del proyecto - Budget Buddy

**Definición:**

Budget Buddy es un asistente inteligente para la gestión de gastos personales en español. Su función principal es recibir facturas y recibos (PDF estándar SAT o fotos de supermercados) y organizar automáticamente la información, identificando montos, fechas, tiendas, productos y categorías de gasto, en moneda quetzal (GTQ).

**Objetivos:**

* Permitir consultas en lenguaje natural sobre gastos, resúmenes por categoría, tienda o periodo.
* Extraer datos financieros de documentos para generar información estructurada (JSON) y reportes automáticos.

**Alcance:**

* Documentos en español: facturas SAT PDF y fotos de recibos físicos.
* Extracción de datos clave: montos, fechas, tiendas, productos, categorías de gasto.
* Procesamiento mediante pipeline modular: imagen → OCR / Document Understanding → LLM → consultas en lenguaje natural.

**Modelos previstos:**

1. **TrOCR** – OCR principal para texto impreso en español.
2. **LayoutLMv3** – Comprensión de layout y relaciones espaciales en documentos complejos.
3. **LLaMA 2 – 7B** – LLM principal para análisis semántico, resúmenes y respuestas a consultas en español.
4. **Donut** – Uso secundario, para pruebas comparativas o experimentos de estructuración de documentos.
