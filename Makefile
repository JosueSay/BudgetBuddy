.PHONY: preprocess
preprocess:
	 PYTHONPATH=. python scripts/python/preprocess.py --hash --overwrite

.PHONY: resolve resolve-apply duplicate-undo
resolve:
	 PYTHONPATH=. python scripts/python/resolve_duplicates.py --by name

resolve-apply:
	 PYTHONPATH=. python scripts/python/resolve_duplicates.py --by name --apply

duplicate-undo:
	 @echo "uso: make duplicate-undo RUN=run_YYYYmmdd_HHMMSS"
	 PYTHONPATH=. python scripts/python/resolve_duplicates.py --undo "data/interim/.trash/$(RUN)"

.PHONY: web
web:
	 PYTHONPATH=. uvicorn src.budget_buddy.webapp.main:app --host 0.0.0.0 --port 8000 --reload

.PHONY: build-train build-train-undo
build-train:
	 PYTHONPATH=. python scripts/python/build_train_split.py

build-train-undo:
	 @echo "uso: make build-train-undo RUN=run_YYYYmmdd_HHMMSS"
	 PYTHONPATH=. python scripts/python/build_train_split.py --undo "data/splits/.trash/$(RUN)"

# device: cuda, cpu, auto

.PHONY: ocr
ocr:
	 PYTHONPATH=. python src/budget_buddy/ocr/trocr_infer.py --device cuda

.PHONY: ocr-fast
ocr-fast:
	 PYTHONPATH=. python src/budget_buddy/ocr/trocr_infer.py --max-per-category 3 --device cuda

.PHONY: check-gpu
check-gpu:
	 PYTHONPATH=. python -c "import torch; print('cuda:', torch.cuda.is_available(), '->', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'cpu')"
