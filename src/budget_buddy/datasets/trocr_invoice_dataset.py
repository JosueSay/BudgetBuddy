from pathlib import Path
from typing import Any
import xml.etree.ElementTree as ET

from PIL import Image
import torch
from torch.utils.data import Dataset


ROOT = Path(".").resolve()
TRAIN_SPLIT_ROOT = ROOT / "data" / "splits" / "train"
IMAGES_TRAIN_ROOT = ROOT / "data" / "interim" / "images" / "train"


def findImageForPdf(category: str, stem: str) -> Path | None:
    # busca imagen rasterizada asociada al pdf
    img_dir = IMAGES_TRAIN_ROOT / category
    if not img_dir.exists():
        return None

    candidate = img_dir / f"{stem}_p1.png"
    if candidate.exists():
        return candidate

    matches = sorted(img_dir.glob(f"{stem}_p*.png"))
    return matches[0] if matches else None


def parseFelXml(xml_path: Path) -> dict:
    # extrae campos clave del xml fel
    ns = {
        "dte": "http://www.sat.gob.gt/dte/fel/0.2.0",
    }

    tree = ET.parse(xml_path)
    root = tree.getroot()

    datos_generales = root.find(".//dte:DatosGenerales", ns)
    emisor = root.find(".//dte:Emisor", ns)
    totales = root.find(".//dte:Totales", ns)
    gran_total = totales.find("dte:GranTotal", ns) if totales is not None else None

    emisor_nombre = emisor.get("NombreEmisor") if emisor is not None else ""

    fecha_emision_raw = (
        datos_generales.get("FechaHoraEmision") if datos_generales is not None else ""
    )
    fecha_emision = ""
    if fecha_emision_raw:
        fecha_emision = fecha_emision_raw.split("T")[0]

    moneda = datos_generales.get("CodigoMoneda") if datos_generales is not None else ""

    total_str = gran_total.text.strip() if gran_total is not None and gran_total.text else ""

    return {
        "emisor_nombre": emisor_nombre,
        "fecha_emision": fecha_emision,
        "gran_total": total_str,
        "moneda": moneda,
    }


def buildTargetText(fields: dict) -> str:
    # construye string objetivo estable para el modelo
    emisor = fields.get("emisor_nombre", "") or ""
    fecha = fields.get("fecha_emision", "") or ""
    total = fields.get("gran_total", "") or ""
    moneda = fields.get("moneda", "") or ""

    lines = [
        f"EMISOR: {emisor}",
        f"FECHA: {fecha}",
        f"TOTAL: {total}",
        f"MONEDA: {moneda}",
    ]
    return "\n".join(lines).strip()


def collectInvoicePairs() -> list[dict]:
    # recorre data/splits/train y arma lista de pares (imagen, xml → texto)
    pairs: list[dict] = []

    if not TRAIN_SPLIT_ROOT.exists():
        raise FileNotFoundError(f"no existe {TRAIN_SPLIT_ROOT}, corre build-train primero")

    for cat_dir in sorted(TRAIN_SPLIT_ROOT.iterdir()):
        if not cat_dir.is_dir():
            continue

        category = cat_dir.name
        pdf_paths = sorted(cat_dir.glob("*.pdf"))

        for pdf_path in pdf_paths:
            stem = pdf_path.stem
            xml_path = cat_dir / f"{stem}.xml"
            if not xml_path.exists():
                continue

            img_path = findImageForPdf(category, stem)
            if img_path is None or not img_path.exists():
                continue

            fields = parseFelXml(xml_path)
            target_text = buildTargetText(fields)
            if not target_text:
                continue

            pairs.append(
                {
                    "category": category,
                    "pdf_path": str(pdf_path),
                    "xml_path": str(xml_path),
                    "image_path": str(img_path),
                    "target_text": target_text,
                }
            )

    if not pairs:
        raise RuntimeError("no se encontraron pares (pdf, xml, imagen) válidos en train")

    return pairs


class TrOcrInvoiceDataset(Dataset):
    # dataset pytorch para finetuning trocr con facturas fel
    def __init__(self, processor, pairs: list[dict], max_target_length: int = 128):
        self.processor = processor
        self.pairs = pairs
        self.max_target_length = max_target_length

    def __len__(self) -> int:
        return len(self.pairs)

    def __getitem__(self, idx: int) -> dict[str, Any]:
        row = self.pairs[idx]
        img = Image.open(row["image_path"]).convert("RGB")
        text = row["target_text"]

        pixel_values = self.processor(
            images=img,
            return_tensors="pt",
        ).pixel_values[0]

        with self.processor.as_target_processor():
            labels = self.processor(
                text,
                max_length=self.max_target_length,
                truncation=True,
                return_tensors="pt",
            ).input_ids[0]

        return {
            "pixel_values": pixel_values,
            "labels": labels,
        }
