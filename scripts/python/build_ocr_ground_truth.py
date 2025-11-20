import argparse
import random
from pathlib import Path

import pandas as pd

from src.budget_buddy.utils.io import ensureDirs, toCsv


ROOT = Path(".")
SPLITS_DIR = ROOT / "data" / "splits"
PROC_DIR = ROOT / "data" / "processed"


def findSplitRoot(split_name: str) -> Path:
    split_root = SPLITS_DIR / split_name
    if not split_root.exists():
        raise FileNotFoundError(f"no existe {split_root}, corre build-train primero")
    return split_root


def samplePdfsFromSplit(split_root: Path, per_category: int, seed: int | None = None):
    if seed is not None:
        random.seed(seed)

    rows = []

    for cat_dir in sorted(split_root.iterdir()):
        if not cat_dir.is_dir():
            continue

        category = cat_dir.name
        pdf_paths = sorted(cat_dir.glob("*.pdf"))

        if not pdf_paths:
            continue

        if per_category > 0 and len(pdf_paths) > per_category:
            sampled = random.sample(pdf_paths, per_category)
        else:
            sampled = pdf_paths

        for pdf_path in sampled:
            rows.append(
                {
                    "pdf_path": str(pdf_path),
                    "category": category,
                    "pdf_filename": pdf_path.name,
                    # campos de verdad terreno a rellenar a mano
                    "emisor": "",
                    "fecha_emision": "",
                    "total": "",
                    "moneda": "",
                }
            )

    return rows


def buildGroundTruthCsv(split_name: str, per_category: int, seed: int, output_path: Path, overwrite: bool):
    ensureDirs([PROC_DIR])

    if output_path.exists() and not overwrite:
        raise FileExistsError(
            f"{output_path} ya existe. "
            f"usa --overwrite si quieres regenerarlo."
        )

    split_root = findSplitRoot(split_name)
    rows = samplePdfsFromSplit(split_root, per_category=per_category, seed=seed)

    if not rows:
        print("no se encontraron PDFs para el split indicado")
        return

    df = pd.DataFrame(rows)
    toCsv(df, output_path, overwrite=True)

    print(f"ground truth candidates guardados en: {output_path}")
    print(f"- total filas: {len(df)}")
    print("- ahora puedes abrir el CSV y rellenar emisor, fecha_emision, total, moneda")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--split",
        type=str,
        default="train",
        help="split a usar (por ahora soportado: train)",
    )
    ap.add_argument(
        "--per-category",
        type=int,
        default=3,
        help="número de PDFs por categoría (0 = todos)",
    )
    ap.add_argument(
        "--seed",
        type=int,
        default=42,
        help="seed para muestreo aleatorio",
    )
    ap.add_argument(
        "--output",
        type=str,
        default="data/processed/ocr_ground_truth_candidates.csv",
        help="ruta del CSV de salida",
    )
    ap.add_argument(
        "--overwrite",
        action="store_true",
        help="si se pasa, sobrescribe el CSV si ya existe",
    )
    args = ap.parse_args()

    output_path = ROOT / args.output

    buildGroundTruthCsv(
        split_name=args.split,
        per_category=args.per_category,
        seed=args.seed,
        output_path=output_path,
        overwrite=args.overwrite,
    )


if __name__ == "__main__":
    main()
