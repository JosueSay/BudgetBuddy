import argparse
import json
from pathlib import Path
import os

os.environ["TRANSFORMERS_NO_TORCHVISION"] = "1"

import torch
from src.budget_buddy.utils.common_models import getDevice, loadTrocrModel

from src.budget_buddy.utils.logging_config import quietHf
quietHf()

from src.budget_buddy.utils.io import ensureDirs
from src.budget_buddy.layout.sat_template import getSatRegionsBoxes
from src.budget_buddy.preprocessing.pdf_loader import iterSplitPdfs
from src.budget_buddy.preprocessing.pdf_to_images import (
    savePdfPagesAsImages,
    loadCachedImages,
)


ROOT = Path(".")
TRAIN_SPLIT_ROOT = ROOT / "data" / "splits" / "train"
OCR_OUTPUT_ROOT = ROOT / "data" / "interim" / "ocr_train"
IMAGE_SPLIT = "train"


def getImagesForPdf(
    category: str,
    pdf_path: Path,
    dpi: int = 300,
    use_cache: bool = True,
):
    # intenta cargar imágenes cacheadas; si no hay, las genera y vuelve a cargar
    images = []

    if use_cache:
        images = loadCachedImages(IMAGE_SPLIT, category, pdf_path)

    if images:
        return images

    # no hay cache → generamos pngs y luego las cargamos
    print("  no hay imágenes cacheadas, generando pngs...")
    savePdfPagesAsImages(
        split=IMAGE_SPLIT,
        category=category,
        pdf_path=pdf_path,
        dpi=dpi,
        overwrite=False,
    )
    images = loadCachedImages(IMAGE_SPLIT, category, pdf_path)

    return images


def ocrSingleImage(
    processor,
    model,
    img,
    device: torch.device,
    max_new_tokens: int = 256,
):
    # corre trocr sobre una sola imagen
    inputs = processor(images=img, return_tensors="pt").to(device)
    with torch.no_grad():
        generated_ids = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
        )
    text = processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
    return text.strip()


def ocrImagesFullPage(
    processor,
    model,
    images,
    device: torch.device,
    max_new_tokens: int = 256,
):
    # ocr estándar por página completa
    page_texts = []

    for idx, img in enumerate(images):
        text = ocrSingleImage(
            processor,
            model,
            img,
            device,
            max_new_tokens=max_new_tokens,
        )
        page_texts.append(text)
        print(f"  página {idx + 1} (full) → {len(text)} chars")

    return page_texts


def ocrImagesSatTemplate(
    processor,
    model,
    images,
    device: torch.device,
    max_new_tokens: int = 256,
):
    # ocr por zonas usando plantilla sat, asumiendo 1 página por factura
    if not images:
        return {}, [], ""

    img = images[0]
    img_width, img_height = img.size
    boxes = getSatRegionsBoxes(img_width, img_height)

    region_texts = {}
    ordered_texts = []

    for region_name, box in boxes.items():
        crop_img = img.crop(box)
        text = ocrSingleImage(
            processor,
            model,
            crop_img,
            device,
            max_new_tokens=max_new_tokens,
        )
        region_texts[region_name] = text
        ordered_texts.append((region_name, text))
        print(f"  region {region_name} → {len(text)} chars")

    parts = [txt for _, txt in ordered_texts if txt]
    full_text = "\n\n".join(parts)

    return region_texts, ordered_texts, full_text


def buildOutputPath(pdf_path: Path, category: str):
    # arma ruta de salida json a partir del pdf y la categoria
    rel_name = pdf_path.stem + ".json"
    out_dir = OCR_OUTPUT_ROOT / category
    out_path = out_dir / rel_name
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_path


def ocrPdf(
    processor,
    model,
    device: torch.device,
    pdf_path: Path,
    category: str,
    mode: str,
    dpi: int,
    use_cache: bool,
    overwrite: bool,
    model_dir: str,
):
    # corre ocr sobre un pdf y guarda json con textos
    out_path = buildOutputPath(pdf_path, category)

    if out_path.exists() and not overwrite:
        print(f"\n[skip] ya existe: {out_path}")
        return out_path

    print(f"\nprocesando pdf: {pdf_path}  |  modo={mode}")

    images = getImagesForPdf(
        category=category,
        pdf_path=pdf_path,
        dpi=dpi,
        use_cache=use_cache,
    )
    if not images:
        print("  no se pudieron obtener imágenes (ni de cache ni nuevas), se omite")
        return None

    if mode == "full":
        page_texts = ocrImagesFullPage(processor, model, images, device)
        full_text = "\n\n".join(page_texts)
        region_texts = {}
    else:
        region_texts, ordered_texts, full_text = ocrImagesSatTemplate(
            processor,
            model,
            images,
            device,
        )
        page_texts = [full_text]

    payload = {
        "pdf_path": str(pdf_path),
        "category": category,
        "model_name": model_dir,
        "num_pages": len(images),
        "page_texts": page_texts,
        "full_text": full_text,
    }

    if region_texts:
        payload["regions"] = {
            name: {
                "text": txt,
            }
            for name, txt in region_texts.items()
        }
        payload["header_text"] = region_texts.get("header", "")
        payload["items_text"] = region_texts.get("items_table", "")

    with out_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"  guardado json OCR en: {out_path}")
    return out_path


def iterTrainPdfs(max_per_category: int | None = None):
    # compat: mantenemos esta función, pero ahora usamos iterSplitPdfs internamente
    if not TRAIN_SPLIT_ROOT.exists():
        raise FileNotFoundError(
            f"no existe {TRAIN_SPLIT_ROOT}, corre build-train primero"
        )

    for category, pdf_path in iterSplitPdfs(
        split="train",
        max_per_category=max_per_category,
    ):
        yield category, pdf_path


def runOcr(
    max_per_category: int | None = None,
    device_preference: str = "auto",
    mode: str = "sat-template",
    dpi: int = 300,
    use_cache: bool = True,
    overwrite: bool = False,
    model_dir: str = "qantev/trocr-base-spanish",
):
    ensureDirs([OCR_OUTPUT_ROOT])

    device = getDevice(device_preference)
    print(f"usando device: {device}")
    if device.type == "cuda":
        print(f"cuda disponible, device name: {torch.cuda.get_device_name(0)}")

    processor, model = loadTrocrModel(model_dir, device)

    processed = 0
    for category, pdf_path in iterTrainPdfs(max_per_category=max_per_category):
        out_path = ocrPdf(
            processor=processor,
            model=model,
            device=device,
            pdf_path=pdf_path,
            category=category,
            mode=mode,
            dpi=dpi,
            use_cache=use_cache,
            overwrite=overwrite,
            model_dir=model_dir,
        )
        if out_path is not None:
            processed += 1

    print(f"\nocr terminado, facturas procesadas: {processed}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--max-per-category",
        type=int,
        default=None,
        help="límite opcional de PDFs por categoría para prueba rápida",
    )
    parser.add_argument(
        "--device",
        choices=["auto", "cpu", "cuda"],
        default="auto",
        help="device a usar: auto, cpu o cuda",
    )
    parser.add_argument(
        "--mode",
        choices=["full", "sat-template"],
        default="sat-template",
        help="estrategia de ocr: página completa o zonas sat-template",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=450,
        help="dpi usados al generar las imágenes (cuando no hay cache)",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="si se pasa, ignora cache de imágenes y las regenera",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="si se pasa, recalcula json aunque ya exista",
    )
    parser.add_argument(
        "--model-dir",
        type=str,
        default="qantev/trocr-base-spanish",
        help="ruta al modelo (baseline o fine-tuned)",
    )

    args = parser.parse_args()

    runOcr(
        max_per_category=args.max_per_category,
        device_preference=args.device,
        mode=args.mode,
        dpi=args.dpi,
        use_cache=not args.no_cache,
        overwrite=args.overwrite,
        model_dir=args.model_dir,
    )


if __name__ == "__main__":
    main()
