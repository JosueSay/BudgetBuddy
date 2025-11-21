import argparse
import json
from datetime import datetime
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
from src.budget_buddy.preprocessing.pdf_to_images import savePdfPagesAsImages, loadCachedImages


ROOT = Path(".")
TRAIN_SPLIT_ROOT = ROOT / "data" / "splits" / "train"
RUN_ID = datetime.now().strftime("%Y%m%d_%H%M%S")
OCR_OUTPUT_ROOT = ROOT / "data" / "interim" / "ocr_train" / RUN_ID
IMAGE_SPLIT = "train"


def getImagesForPdf(
    category: str,
    pdf_path: Path,
    dpi: int = 300,
    use_cache: bool = True,
):
    # intenta cargar imágenes cacheadas
    images = []

    if use_cache:
        images = loadCachedImages(IMAGE_SPLIT, category, pdf_path)

    if images:
        return images

    # si no hay cache se generan los pngs
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
    # corre trocr para una sola imagen
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
    debug_dir: Path | None = None,
    pdf_stem: str | None = None,
    category: str | None = None,
):
    page_texts = []

    # prepara carpeta de debug si aplica
    sample_dir = None
    if debug_dir is not None and pdf_stem is not None and category is not None:
        sample_dir = debug_dir / category / pdf_stem
        sample_dir.mkdir(parents=True, exist_ok=True)

    for idx, img in enumerate(images):
        # guarda imagen para debug
        if sample_dir is not None:
            img.save(sample_dir / f"page_{idx+1}.png")

        text = ocrSingleImage(
            processor,
            model,
            img,
            device,
            max_new_tokens=max_new_tokens,
        )
        page_texts.append(text)

        # guarda texto para debug
        if sample_dir is not None:
            (sample_dir / f"page_{idx+1}.txt").write_text(
                text,
                encoding="utf-8",
            )

        print(f"\tpágina {idx + 1} (full) → {len(text)} chars")

    return page_texts


def ocrImagesSatTemplate(
    processor,
    model,
    images,
    device: torch.device,
    max_new_tokens: int = 256,
    debug_dir: Path | None = None,
    pdf_stem: str | None = None,
    category: str | None = None,
):
    # retorna si no hay imágenes
    if not images:
        return {}, [], ""

    img = images[0]
    img_width, img_height = img.size

    # obtiene cajas del template sat
    boxes = getSatRegionsBoxes(img_width, img_height)

    region_texts = {}
    ordered_texts = []

    # prepara carpeta de debug si aplica
    sample_dir = None
    if debug_dir is not None and pdf_stem is not None and category is not None:
        sample_dir = debug_dir / category / pdf_stem
        sample_dir.mkdir(parents=True, exist_ok=True)

    for region_name, box in boxes.items():
        crop_img = img.crop(box)

        # guarda recorte si debug
        if sample_dir is not None:
            crop_img.save(sample_dir / f"{region_name}.png")

        text = ocrSingleImage(
            processor,
            model,
            crop_img,
            device,
            max_new_tokens=max_new_tokens,
        )

        region_texts[region_name] = text
        ordered_texts.append((region_name, text))

        # guarda texto si debug
        if sample_dir is not None:
            (sample_dir / f"{region_name}.txt").write_text(
                text,
                encoding="utf-8",
            )

        print(f"\tregion {region_name} → {len(text)} chars")

    # une textos en orden
    parts = [txt for _, txt in ordered_texts if txt]
    full_text = "\n\n".join(parts)

    return region_texts, ordered_texts, full_text


def buildOutputPath(pdf_path: Path, category: str):
    # arma ruta de salida para json
    rel_name = pdf_path.stem + ".json"
    out_dir = OCR_OUTPUT_ROOT / category
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir / rel_name


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
    debug_dir: Path | None = None,
):
    # salida esperada para el json final
    out_path = buildOutputPath(pdf_path, category)

    if out_path.exists() and not overwrite:
        print(f"\n[skip] ya existe: {out_path}")
        return out_path

    print(f"\nprocesando pdf: {pdf_path}  |  modo={mode}")

    # cargar imágenes del pdf (cache o raster)
    images = getImagesForPdf(
        category=category,
        pdf_path=pdf_path,
        dpi=dpi,
        use_cache=use_cache,
    )
    if not images:
        print("\tno se pudieron obtener imágenes, se omite")
        return None

    # nombre base para guardados de debug
    pdf_stem = pdf_path.stem

    # elegir flujo de ocr según modo
    if mode == "full":
        page_texts = ocrImagesFullPage(
            processor,
            model,
            images,
            device,
            debug_dir=debug_dir,
            pdf_stem=pdf_stem,
            category=category,
        )
        full_text = "\n\n".join(page_texts)
        region_texts = {}
    else:
        region_texts, ordered_texts, full_text = ocrImagesSatTemplate(
            processor,
            model,
            images,
            device,
            debug_dir=debug_dir,
            pdf_stem=pdf_stem,
            category=category,
        )
        page_texts = [full_text]

    # construir json para guardar resultados
    payload = {
        "pdf_path": str(pdf_path),
        "category": category,
        "model_name": model_dir,
        "num_pages": len(images),
        "page_texts": page_texts,
        "full_text": full_text,
    }

    # agregar regiones si las hay
    if region_texts:
        payload["regions"] = {
            name: {"text": txt}
            for name, txt in region_texts.items()
        }
        payload["header_text"] = region_texts.get("header", "")
        payload["items_text"] = region_texts.get("items_table", "")

    # escribir json en disco
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"\tguardado json OCR en: {out_path}")
    return out_path


def iterTrainPdfs(max_per_category: int | None = None):
    # verificar que el split exista
    if not TRAIN_SPLIT_ROOT.exists():
        raise FileNotFoundError(
            f"no existe {TRAIN_SPLIT_ROOT}, corre build-train primero"
        )

    # iterar pdfs del split de entrenamiento
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
    debug_dir: Path | None = None,
):
    # asegurar carpetas de salida
    ensureDirs([OCR_OUTPUT_ROOT])

    # seleccionar device según preferencia
    device = getDevice(device_preference)
    print(f"usando device: {device}")
    if device.type == "cuda":
        print(f"cuda disponible, device name: {torch.cuda.get_device_name(0)}")

    # cargar modelo trocr
    processor, model = loadTrocrModel(model_dir, device)

    processed = 0
    # recorrer todos los pdfs del entrenamiento
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
            debug_dir=debug_dir,
        )

        if out_path is not None:
            processed += 1

    print(f"\nocr terminado, facturas procesadas: {processed}")


def main():
    # parser para flags CLI
    parser = argparse.ArgumentParser()

    # límite opcional para pruebas rápidas
    parser.add_argument(
        "--max-per-category",
        type=int,
        default=None,
        help="límite opcional de PDFs por categoría para prueba rápida",
    )

    # control del dispositivo
    parser.add_argument(
        "--device",
        choices=["auto", "cpu", "cuda"],
        default="auto",
        help="device a usar: auto, cpu o cuda",
    )

    # modo de ocr
    parser.add_argument(
        "--mode",
        choices=["full", "sat-template"],
        default="sat-template",
        help="estrategia de ocr: página completa o zonas sat-template",
    )

    # dpi para generar imágenes
    parser.add_argument(
        "--dpi",
        type=int,
        default=450,
        help="dpi usados al generar las imágenes (cuando no hay cache)",
    )

    # forzar regeneración de imágenes
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="si se pasa, ignora cache de imágenes y las regenera",
    )

    # sobrescribir json existente
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="si se pasa, recalcula json aunque ya exista",
    )

    # ruta del modelo
    parser.add_argument(
        "--model-dir",
        type=str,
        default="qantev/trocr-base-spanish",
        help="ruta al modelo (baseline o fine-tuned)",
    )

    # guardar recortes para debugging
    parser.add_argument(
        "--debug-crops-dir",
        type=str,
        default=None,
        help="si se pasa, guarda recortes e inputs del modelo en esta carpeta",
    )

    args = parser.parse_args()

    # crear path solo si se definió
    debug_dir = Path(args.debug_crops_dir) if args.debug_crops_dir else None

    runOcr(
        max_per_category=args.max_per_category,
        device_preference=args.device,
        mode=args.mode,
        dpi=args.dpi,
        use_cache=not args.no_cache,
        overwrite=args.overwrite,
        model_dir=args.model_dir,
        debug_dir=debug_dir,
    )


if __name__ == "__main__":
    main()

