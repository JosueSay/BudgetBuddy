###########################################################################
#                          Budget Buddy — Makefile                        
#                         Procesamiento / OCR / NLP                      
###########################################################################

# Variables generales ------------------------------------------------------

PYTHON := PYTHONPATH=. python
DEBUG_RUN := $(shell date +"%Y%m%d_%H%M%S")
MODEL_NAME ?= default_model
DEBUG_DIR := outputs/debug/$(MODEL_NAME)_$(DEBUG_RUN)

###########################################################################
#                              PREPROCESAMIENTO                          
###########################################################################

.PHONY: preprocess
preprocess:  ## Preprocesa PDFs y genera hashes
	$(PYTHON) scripts/python/preprocess.py --hash --overwrite


###########################################################################
#                          RESOLUCIÓN DE DUPLICADOS                       
###########################################################################

.PHONY: resolve resolve-apply duplicate-undo
resolve:  ## Detecta duplicados por nombre
	$(PYTHON) scripts/python/resolve_duplicates.py --by name

resolve-apply:  ## Aplica la resolución de duplicados
	$(PYTHON) scripts/python/resolve_duplicates.py --by name --apply

duplicate-undo: ## Revierte una ejecución previa
	@echo "uso: make duplicate-undo RUN=run_YYYYmmdd_HHMMSS"
	$(PYTHON) scripts/python/resolve_duplicates.py --undo "data/interim/.trash/$(RUN)"


###########################################################################
#                                  WEB APP                                
###########################################################################

.PHONY: web
web:  ## Inicia el servidor de categorización
	PYTHONPATH=. uvicorn src.budget_buddy.webapp.main:app --host 0.0.0.0 --port 8000 --reload


###########################################################################
#                           SEPARACIÓN DE CATEGORÍAS                      
###########################################################################

.PHONY: build-train build-train-undo
build-train: ## Construye los splits de entrenamiento
	$(PYTHON) scripts/python/build_train_split.py

build-train-undo: ## Revierte split anterior
	@echo "uso: make build-train-undo RUN=run_YYYYmmdd_HHMMSS"
	$(PYTHON) scripts/python/build_train_split.py --undo "data/splits/.trash/$(RUN)"


###########################################################################
#                           RASTERIZACIÓN DE IMÁGENES                     
###########################################################################

.PHONY: build-images build-images-fast
build-images:  ## Genera PNGs (cache respetado)
	@echo "📄 Generando imágenes (cache activado). Para sobrescribir: make build-images OVERWRITE=1"
	$(PYTHON) scripts/python/build_ocr_images.py --split train --dpi 450 $(if $(OVERWRITE),--overwrite,)

build-images-fast: ## Genera pocas imágenes por categoría
	$(PYTHON) scripts/python/build_ocr_images.py --split train --dpi 450 --max-per-category 2 $(if $(OVERWRITE),--overwrite,)


###########################################################################
#                               OCR — MODELO BASE                         
###########################################################################

.PHONY: ocr ocr-fast ocr-overwrite ocr-no-cache ocr-full
ocr:
	@echo "🔎 OCR usando modelo base"
	$(PYTHON) src/budget_buddy/ocr/trocr_infer.py --device cuda

ocr-fast:
	@echo "⚡ OCR rápido (modelo base)"
	$(PYTHON) src/budget_buddy/ocr/trocr_infer.py --max-per-category 3 --device cuda

ocr-overwrite:
	@echo "♻️ Recalculando JSON OCR"
	$(PYTHON) src/budget_buddy/ocr/trocr_infer.py --device cuda --overwrite

ocr-no-cache:
	@echo "🚫 Ignorando cache de imágenes"
	$(PYTHON) src/budget_buddy/ocr/trocr_infer.py --device cuda --no-cache --overwrite

ocr-full:
	@echo "📄 OCR página completa"
	$(PYTHON) src/budget_buddy/ocr/trocr_infer.py --device cuda --mode full


###########################################################################
#                   FINETUNING TrOCR — Variantes FEL                      
###########################################################################

# --- FULL PAGE ---
.PHONY: ocr-train-fel-full
ocr-train-fel-full: ## Full page sin augment
	@echo "🧠 Finetuning TrOCR FEL FULL PAGE"
	$(PYTHON) scripts/python/train_trocr_fel.py \
		--device cuda \
		--output-dir models/trocr_fel_full_v1 \
		--epochs 4 --train-batch-size 4 --eval-batch-size 4 \
		--lr 1e-5 --warmup-ratio 0.05 \
		--image-mode full

# --- HEADER ---
.PHONY: ocr-train-fel-header
ocr-train-fel-header: ## Sat-header sin augment
	@echo "🧠 Finetuning TrOCR FEL HEADER"
	$(PYTHON) scripts/python/train_trocr_fel.py \
		--device cuda \
		--output-dir models/trocr_fel_header_v1 \
		--epochs 4 --train-batch-size 4 --eval-batch-size 4 \
		--lr 1e-5 --warmup-ratio 0.05 \
		--image-mode sat-header

# --- HEADER + AUGMENT ---
.PHONY: ocr-train-fel-header-aug
ocr-train-fel-header-aug: ## Sat-header con augment
	@echo "🧠 Finetuning TrOCR FEL HEADER + AUGMENT"
	$(PYTHON) scripts/python/train_trocr_fel.py \
		--device cuda \
		--output-dir models/trocr_fel_header_aug_v1 \
		--epochs 4 --train-batch-size 4 --eval-batch-size 4 \
		--lr 1e-5 --warmup-ratio 0.05 \
		--image-mode sat-header \
		--use-augment


###########################################################################
#           COMANDO ÚNICO PARA EJECUTAR TODOS LOS TUNINGS          
###########################################################################

.PHONY: ocr-train-all
ocr-train-all: ## Ejecuta full + header + header-aug
	@echo "🚀 Ejecutando TODOS los fine-tuning FEL..."
	$(MAKE) ocr-train-fel-full
	$(MAKE) ocr-train-fel-header
	$(MAKE) ocr-train-fel-header-aug
	@echo "🎉 Fine-tuning FEL completado!"


###########################################################################
#                 OCR USANDO MODELOS FINETUNED (FEL)                      
###########################################################################

.PHONY: ocr-fel ocr-fel-fast ocr-fel-full ocr-fel-full-overwrite ocr-fel-debug

ocr-fel:
	$(PYTHON) src/budget_buddy/ocr/trocr_infer.py --device cuda --model-dir models/trocr_fel_header_v1 $(if $(OVERWRITE),--overwrite,)

ocr-fel-fast:
	$(PYTHON) src/budget_buddy/ocr/trocr_infer.py --max-per-category 3 --device cuda --model-dir models/trocr_fel_header_v1

ocr-fel-full:
	$(PYTHON) src/budget_buddy/ocr/trocr_infer.py --device cuda --mode full --model-dir models/trocr_fel_full_v1

ocr-fel-full-overwrite:
	$(PYTHON) src/budget_buddy/ocr/trocr_infer.py --device cuda --mode full --model-dir models/trocr_fel_full_v1 --overwrite

.PHONY: ocr-fel-aug
ocr-fel-aug:
	$(PYTHON) src/budget_buddy/ocr/trocr_infer.py --device cuda --model-dir models/trocr_fel_header_aug_v1 $(if $(OVERWRITE),--overwrite,)


# --- DEBUG CON CARPETAS SEPARADAS ---
ocr-fel-debug: ## Debug con crops + textos por región
	@echo "🧪 Debug OCR → $(DEBUG_DIR)"
	mkdir -p $(DEBUG_DIR)
	$(PYTHON) src/budget_buddy/ocr/trocr_infer.py \
		--device cuda \
		--mode sat-template \
		--model-dir models/$(MODEL_NAME) \
		--debug-crops-dir $(DEBUG_DIR) \
		--overwrite

.PHONY: ocr-all
ocr-all:  ## Genera JSONs con modelo base + todos los fine-tuned
	@echo "🧾 OCR → modelo BASE"
	$(MAKE) ocr-overwrite

	@echo "🧾 OCR → modelo FEL FULL PAGE"
	$(MAKE) ocr-fel-full-overwrite

	@echo "🧾 OCR → modelo FEL HEADER"
	$(MAKE) ocr-fel OVERWRITE=1

	@echo "🧾 OCR → modelo FEL HEADER + AUGMENT"
	$(MAKE) ocr-fel-aug OVERWRITE=1

	@echo "🎉 OCR completado para base + full + header + header-aug"


###########################################################################
#               DEBUG OCR – TODOS LOS MODELOS AUTOMÁTICAMENTE             
###########################################################################
.PHONY: ocr-base-debug
ocr-base-debug:
	@echo "🧪 Debug OCR BASE"
	$(PYTHON) src/budget_buddy/ocr/trocr_infer.py \
		--device cuda \
		--mode sat-template \
		--model-dir qantev/trocr-base-spanish \
		--debug-crops-dir outputs/debug/base_$(DEBUG_RUN) \
		--overwrite

.PHONY: ocr-debug-all
ocr-debug-all:  ## Ejecuta debug para modelo base + todos los fine-tuned
	@echo "🧪 Debug OCR → modelos: base, full, header, header-aug"

	$(MAKE) ocr-base-debug
	$(MAKE) ocr-fel-debug MODEL_NAME=trocr_fel_full_v1
	$(MAKE) ocr-fel-debug MODEL_NAME=trocr_fel_header_v1
	$(MAKE) ocr-fel-debug MODEL_NAME=trocr_fel_header_aug_v1

	@echo "🎉 Debug OCR completado para todos los modelos."


###########################################################################
#                          UTILIDADES OCR                                
###########################################################################

.PHONY: ocr-gt-sample
ocr-gt-sample:
	$(PYTHON) scripts/python/build_ocr_ground_truth.py --split train --per-category 3 --overwrite


###########################################################################
#                              TEST GPU                                    
###########################################################################

.PHONY: check-gpu
check-gpu:
	$(PYTHON) -c "import torch; print('cuda:', torch.cuda.is_available(), '->', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'cpu')"

