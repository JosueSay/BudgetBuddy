from pathlib import Path
from pdf2image import convert_from_path
from PIL import Image

from src.budget_buddy.utils.io import ensureDirs
from src.budget_buddy.preprocessing.pdf_loader import iterSplitPdfs, getSplitRoot


ROOT = Path(".")
INTERIM_ROOT = ROOT / "data" / "interim"
IMAGES_ROOT = INTERIM_ROOT / "images"


def pdfToImages(pdf_path: Path, dpi: int = 450) -> list[Image.Image]:
    # convierte pdf a páginas en memoria
    return convert_from_path(str(pdf_path), dpi=dpi, fmt="png", grayscale=True)


def getImagesDir(split: str, category: str) -> Path:
    # ruta base donde se guardarán las imágenes
    return IMAGES_ROOT / split / category


def buildImageFilename(pdf_path: Path, page_idx: int) -> str:
    # nombre consistente por página
    return f"{pdf_path.stem}_p{page_idx + 1}.png"


def savePdfPagesAsImages(
    split: str,
    category: str,
    pdf_path: Path,
    dpi: int = 450,
    overwrite: bool = False,
) -> list[Path]:
    # guarda cada página rasterizada en disco
    out_dir = getImagesDir(split, category)
    ensureDirs([out_dir])

    images = pdfToImages(pdf_path, dpi=dpi)
    saved_paths: list[Path] = []

    if not images:
        return saved_paths

    for idx, img in enumerate(images):
        fname = buildImageFilename(pdf_path, idx)
        out_path = out_dir / fname

        if out_path.exists() and not overwrite:
            # ya existe y no se debe sobrescribir
            saved_paths.append(out_path)
            continue

        if img.mode != "RGB":
            # trocr requiere rgb
            img = img.convert("RGB")

        img.save(out_path, format="PNG", dpi=(dpi, dpi))
        saved_paths.append(out_path)

    return saved_paths


def loadCachedImages(
    split: str,
    category: str,
    pdf_path: Path,
) -> list[Image.Image]:
    # carga imágenes previamente guardadas
    out_dir = getImagesDir(split, category)
    if not out_dir.exists():
        return []

    pattern = f"{pdf_path.stem}_p*.png"
    img_paths = sorted(out_dir.glob(pattern))

    images: list[Image.Image] = []
    for path in img_paths:
        images.append(Image.open(path))

    return images


def buildImagesForSplit(
    split: str = "train",
    dpi: int = 450,
    max_per_category: int | None = None,
    overwrite: bool = False,
) -> None:
    # procesa todos los pdfs del split
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
