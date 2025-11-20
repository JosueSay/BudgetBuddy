.PHONY: preprocess
preprocess:
	 PYTHONPATH=. python scripts/python/preprocess.py --hash --overwrite

.PHONY: resolve resolve-apply undo
resolve:
	 PYTHONPATH=. python scripts/python/resolve_duplicates.py --by name

resolve-apply:
	 PYTHONPATH=. python scripts/python/resolve_duplicates.py --by name --apply

undo:
	 @echo "uso: make undo RUN=run_YYYYmmdd_HHMMSS"
	 PYTHONPATH=. python scripts/python/resolve_duplicates.py --undo "data/interim/.trash/$(RUN)"

.PHONY: web
web:
	 PYTHONPATH=. uvicorn src.budget_buddy.webapp.main:app --host 0.0.0.0 --port 8000 --reload

.PHONY: build-train
build-train:
	 PYTHONPATH=. python scripts/python/build_train_split.py
