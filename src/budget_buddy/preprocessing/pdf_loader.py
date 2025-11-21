from pathlib import Path
from typing import Iterator, Tuple

ROOT = Path(".")
SPLITS_ROOT = ROOT / "data" / "splits"


def getSplitRoot(split: str) -> Path:
    # normaliza y valida el split
    split = split.lower()
    if split not in {"train", "test"}:
        raise ValueError(f"split inválido: {split} (usa 'train' o 'test')")

    split_root = SPLITS_ROOT / split
    # verifica que exista el directorio
    if not split_root.exists():
        raise FileNotFoundError(f"no existe el directorio de split: {split_root}")

    return split_root


def iterSplitPdfs(
    split: str = "train",
    max_per_category: int | None = None,
) -> Iterator[Tuple[str, Path]]:
    # itera por categorías y pdfs dentro del split
    split_root = getSplitRoot(split)

    for cat_dir in sorted(split_root.iterdir()):
        if not cat_dir.is_dir():
            continue

        category = cat_dir.name
        pdf_paths = sorted(cat_dir.glob("*.pdf"))

        # limita pdfs por categoría si se pide
        if max_per_category is not None:
            pdf_paths = pdf_paths[:max_per_category]

        for pdf_path in pdf_paths:
            yield category, pdf_path
