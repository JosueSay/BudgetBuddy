# preprocesamiento de PDFs
.PHONY: preprocess
preprocess:
	 PYTHONPATH=. python scripts/python/preprocess.py --hash --overwrite


# resolución de duplicados
.PHONY: resolve resolve-apply duplicate-undo
resolve:
	 PYTHONPATH=. python scripts/python/resolve_duplicates.py --by name

resolve-apply:
	 PYTHONPATH=. python scripts/python/resolve_duplicates.py --by name --apply

duplicate-undo:
	 @echo "uso: make duplicate-undo RUN=run_YYYYmmdd_HHMMSS"
	 PYTHONPATH=. python scripts/python/resolve_duplicates.py --undo "data/interim/.trash/$(RUN)"


# web para categorizar facturas
.PHONY: web
web:
	 PYTHONPATH=. uvicorn src.budget_buddy.webapp.main:app --host 0.0.0.0 --port 8000 --reload


# separación de categorias
.PHONY: build-train build-train-undo
build-train:
	 PYTHONPATH=. python scripts/python/build_train_split.py

build-train-undo:
	 @echo "uso: make build-train-undo RUN=run_YYYYmmdd_HHMMSS"
	 PYTHONPATH=. python scripts/python/build_train_split.py --undo "data/splits/.trash/$(RUN)"


# rasterizacion imagenes
.PHONY: build-images
build-images:
	@echo "📄 Generando imágenes (cache activado). Para sobrescribir: make build-images OVERWRITE=1"
	PYTHONPATH=. python scripts/python/build_ocr_images.py --split train --dpi 450 $(if $(OVERWRITE),--overwrite,)

.PHONY: build-images-fast
build-images-fast:
	PYTHONPATH=. python scripts/python/build_ocr_images.py --split train --dpi 450 --max-per-category 2 $(if $(OVERWRITE),--overwrite,)


# OCR con plantilla sat
.PHONY: ocr
ocr:
	@echo "🔎 OCR usando cache y GPU (modo plantilla SAT por defecto)"
	PYTHONPATH=. python src/budget_buddy/ocr/trocr_infer.py --device cuda

.PHONY: ocr-fast
ocr-fast:
	@echo "⚡ OCR rápido (3 PDFs por categoría)"
	PYTHONPATH=. python src/budget_buddy/ocr/trocr_infer.py --max-per-category 3 --device cuda

.PHONY: ocr-overwrite
ocr-overwrite:
	@echo "♻️ Recalculando JSON OCR (manteniendo cache de imágenes)"
	PYTHONPATH=. python src/budget_buddy/ocr/trocr_infer.py --device cuda --overwrite

.PHONY: ocr-no-cache
ocr-no-cache:
	@echo "🚫 Ignorando cache de imágenes — regenerando PNGs al vuelo"
	PYTHONPATH=. python src/budget_buddy/ocr/trocr_infer.py --device cuda --no-cache --overwrite

.PHONY: ocr-full
ocr-full:
	@echo "📄 OCR página completa — útil para debugging"
	PYTHONPATH=. python src/budget_buddy/ocr/trocr_infer.py --device cuda --mode full


# fine-tuning TrOCR con facturas FEL
.PHONY: ocr-train-fel
ocr-train-fel:
	@echo "🧠 Finetuning TrOCR con facturas FEL (PDF + XML)…"
	PYTHONPATH=. python scripts/python/train_trocr_fel.py --device cuda --output-dir models/trocr_fel_v1

.PHONY: ocr-train-fel-cpu
ocr-train-fel-cpu:
	@echo "🧠 Finetuning TrOCR con facturas FEL en CPU (modo lento)…"
	PYTHONPATH=. python scripts/python/train_trocr_fel.py --device cpu --output-dir models/trocr_fel_v1

.PHONY: ocr-train-fel-fast
ocr-train-fel-fast:
	@echo "⚡ Finetuning rápido TrOCR FEL (pocas épocas)…"
	PYTHONPATH=. python scripts/python/train_trocr_fel.py --device cuda --output-dir models/trocr_fel_v1_fast --epochs 2 --train-batch-size 2 --eval-batch-size 2


# OCR usando modelo fine-tuned FEL
.PHONY: ocr-fel
ocr-fel:
	@echo "🧾 OCR usando modelo fine-tuned (models/trocr_fel_v1)"
	PYTHONPATH=. python src/budget_buddy/ocr/trocr_infer.py --device cuda --model-dir models/trocr_fel_v1 $(if $(OVERWRITE),--overwrite,)

# OCR comparativo rápido (base vs fine-tuned)
.PHONY: ocr-fel-fast
ocr-fel-fast:
	@echo "⚡ OCR rápido con modelo fine-tuned (3 PDFs por categoría)"
	PYTHONPATH=. python src/budget_buddy/ocr/trocr_infer.py --max-per-category 3 --device cuda --model-dir models/trocr_fel_v1

# OCR completo (full-page) para debugging pero usando el modelo fine-tuned
.PHONY: ocr-fel-full
ocr-fel-full:
	@echo "📄 OCR FULL PAGE usando modelo fine-tuned"
	PYTHONPATH=. python src/budget_buddy/ocr/trocr_infer.py --device cuda --mode full --model-dir models/trocr_fel_v1


# muestras para ocr
.PHONY: ocr-gt-sample
ocr-gt-sample:
	@echo "🎯 Generando muestras para ground truth OCR (rellenar campos en el CSV)…"
	PYTHONPATH=. python scripts/python/build_ocr_ground_truth.py --split train --per-category 3 --overwrite


# test gpu
.PHONY: check-gpu
check-gpu:
	 PYTHONPATH=. python -c "import torch; print('cuda:', torch.cuda.is_available(), '->', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'cpu')"
