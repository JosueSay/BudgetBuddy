from pathlib import Path
from typing import List
import os

from pdf2image import convert_from_path
from PIL import Image

from src.budget_buddy.utils.io import ensureDirs
from src.budget_buddy.preprocessing.pdf_loader import iterSplitPdfs, getSplitRoot


ROOT = Path(".")
INTERIM_ROOT = ROOT / "data" / "interim"
IMAGES_ROOT = INTERIM_ROOT / "images"


def pdfToImages(pdf_path: Path, dpi: int = 300) -> List[Image.Image]:
    # convierte pdf a lista de imágenes PIL
    images = convert_from_path(str(pdf_path), dpi=dpi)
    return images


def getImagesDir(split: str, category: str) -> Path:
    # directorio donde se guardan las imágenes de un split y categoría
    return IMAGES_ROOT / split / category


def buildImageFilename(pdf_path: Path, page_idx: int) -> str:
    # nombre de archivo consistente para cada página
    # ej: ABC123_p1.png
    return f"{pdf_path.stem}_p{page_idx + 1}.png"


def savePdfPagesAsImages(
    split: str,
    category: str,
    pdf_path: Path,
    dpi: int = 300,
    overwrite: bool = False,
) -> List[Path]:
    # rasteriza un pdf y guarda cada página como png
    out_dir = getImagesDir(split, category)
    ensureDirs([out_dir])

    images = pdfToImages(pdf_path, dpi=dpi)
    saved_paths: List[Path] = []

    if not images:
        return saved_paths

    for idx, img in enumerate(images):
        fname = buildImageFilename(pdf_path, idx)
        out_path = out_dir / fname

        if out_path.exists() and not overwrite:
            saved_paths.append(out_path)
            continue

        # garantiza modo rgb para evitar sorpresas
        if img.mode != "RGB":
            img = img.convert("RGB")

        img.save(out_path, format="PNG")
        saved_paths.append(out_path)

    return saved_paths


def loadCachedImages(
    split: str,
    category: str,
    pdf_path: Path,
) -> List[Image.Image]:
    # carga imágenes ya guardadas en disco; si no hay ninguna, devuelve lista vacía
    out_dir = getImagesDir(split, category)
    if not out_dir.exists():
        return []

    pattern = f"{pdf_path.stem}_p*.png"
    img_paths = sorted(out_dir.glob(pattern))
    images: List[Image.Image] = []

    for path in img_paths:
        img = Image.open(path)
        images.append(img)

    return images


def buildImagesForSplit(
    split: str = "train",
    dpi: int = 300,
    max_per_category: int | None = None,
    overwrite: bool = False,
) -> None:
    # genera imágenes para todos los pdfs de un split
    split_root = getSplitRoot(split)
    print(f"generando imágenes para split={split} desde {split_root}")

    total_pdfs = 0
    total_images = 0

    for category, pdf_path in iterSplitPdfs(split=split, max_per_category=max_per_category):
        total_pdfs += 1
        print(f"- [{split}/{category}] {pdf_path.name}")

        saved_paths = savePdfPagesAsImages(
            split=split,
            category=category,
            pdf_path=pdf_path,
            dpi=dpi,
            overwrite=overwrite,
        )
        total_images += len(saved_paths)

    print(f"\nresumen imágenes → split={split}")
    print(f"\tpdfs procesados : {total_pdfs}")
    print(f"\timágenes guardadas: {total_images}")
    print(f"\traíz imágenes   : {IMAGES_ROOT}")
