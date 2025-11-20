import argparse
import json
from pathlib import Path
import os

os.environ["TRANSFORMERS_NO_TORCHVISION"] = "1"

import torch
from pdf2image import convert_from_path
from transformers import TrOCRProcessor, VisionEncoderDecoderModel

from src.budget_buddy.utils.io import ensureDirs


ROOT = Path(".")
TRAIN_SPLIT_ROOT = ROOT / "data" / "splits" / "train"
OCR_OUTPUT_ROOT = ROOT / "data" / "interim" / "ocr_train"

TROCR_MODEL_NAME = "qantev/trocr-base-spanish"


def getDevice(device_preference: str):
    # device_preference: "auto", "cpu", "cuda"
    if device_preference == "cpu":
        return torch.device("cpu")

    if device_preference == "cuda":
        if not torch.cuda.is_available():
            raise RuntimeError("se pidió cuda pero torch.cuda.is_available() es False")
        return torch.device("cuda")

    # modo auto
    if torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


def loadTrocrModel(model_name: str, device: torch.device):
    # carga modelo y processor de trocr
    print(f"cargando modelo TrOCR: {model_name}")
    processor = TrOCRProcessor.from_pretrained(model_name)
    model = VisionEncoderDecoderModel.from_pretrained(model_name)
    model.to(device)
    model.eval()
    return processor, model


def pdfToImages(pdf_path: Path, dpi: int = 300):
    # convierte pdf a lista de imágenes PIL
    # nota: requiere poppler instalado para pdf2image.convert_from_path
    images = convert_from_path(str(pdf_path), dpi=dpi)
    return images


def ocrImages(processor, model, images, device: torch.device, max_new_tokens: int = 256):
    # corre trocr sobre una lista de imágenes y devuelve lista de textos
    page_texts = []

    for idx, img in enumerate(images):
        inputs = processor(images=img, return_tensors="pt").to(device)
        with torch.no_grad():
            generated_ids = model.generate(
                **inputs,
                max_new_tokens=max_new_tokens
            )
        text = processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
        text = text.strip()
        page_texts.append(text)
        print(f"  página {idx + 1}: {len(text)} chars")

    return page_texts


def buildOutputPath(pdf_path: Path, category: str):
    # arma ruta de salida json a partir del pdf y la categoria
    rel_name = pdf_path.stem + ".json"
    out_dir = OCR_OUTPUT_ROOT / category
    out_path = out_dir / rel_name
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_path


def ocrPdf(processor, model, device: torch.device, pdf_path: Path, category: str):
    # corre ocr sobre un pdf completo y guarda json con textos
    print(f"\nprocesando pdf: {pdf_path}")

    images = pdfToImages(pdf_path)
    if not images:
        print("  no se pudieron generar imágenes, se omite")
        return None

    page_texts = ocrImages(processor, model, images, device)
    full_text = "\n\n".join(page_texts)

    out_path = buildOutputPath(pdf_path, category)

    payload = {
        "pdf_path": str(pdf_path),
        "category": category,
        "model_name": TROCR_MODEL_NAME,
        "num_pages": len(page_texts),
        "page_texts": page_texts,
        "full_text": full_text,
    }

    with out_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"  guardado json OCR en: {out_path}")
    return out_path


def iterTrainPdfs(max_per_category: int | None = None):
    # recorre data/splits/train/<categoria>/*.pdf
    if not TRAIN_SPLIT_ROOT.exists():
        raise FileNotFoundError(f"no existe {TRAIN_SPLIT_ROOT}, corre build-train primero")

    for cat_dir in sorted(TRAIN_SPLIT_ROOT.iterdir()):
        if not cat_dir.is_dir():
            continue

        category = cat_dir.name
        pdf_paths = sorted(cat_dir.glob("*.pdf"))

        if max_per_category is not None:
            pdf_paths = pdf_paths[:max_per_category]

        print(f"\ncategoria: {category} (n={len(pdf_paths)})")

        for pdf_path in pdf_paths:
            yield category, pdf_path


def runOcr(max_per_category: int | None = None, device_preference: str = "auto"):
    ensureDirs([OCR_OUTPUT_ROOT])

    device = getDevice(device_preference)
    print(f"usando device: {device}")
    if device.type == "cuda":
        print(f"cuda disponible, device name: {torch.cuda.get_device_name(0)}")

    processor, model = loadTrocrModel(TROCR_MODEL_NAME, device)

    processed = 0
    for category, pdf_path in iterTrainPdfs(max_per_category=max_per_category):
        out_path = ocrPdf(processor, model, device, pdf_path, category)
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
    args = parser.parse_args()

    runOcr(max_per_category=args.max_per_category, device_preference=args.device)


if __name__ == "__main__":
    main()
