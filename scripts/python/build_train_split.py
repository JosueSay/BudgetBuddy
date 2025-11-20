import json
import shutil
from pathlib import Path

import pandas as pd

from src.budget_buddy.utils.io import ensureDirs, toCsv


ROOT = Path(".")
PROC_DIR = ROOT / "data" / "processed"
SPLITS_DIR = ROOT / "data" / "splits"
TRAIN_ROOT = SPLITS_DIR / "train"

CATEGORIES_META_PATH = PROC_DIR / "categories_meta.json"
CATEGORIES_CSV_PATH = PROC_DIR / "categories.csv"

TRAIN_MANIFEST_PATH = PROC_DIR / "train_manifest.csv"
TRAIN_COUNTS_PATH = PROC_DIR / "train_counts.csv"


def loadCategoriesMeta():
    if not CATEGORIES_META_PATH.exists():
        raise FileNotFoundError(f"no se encontró {CATEGORIES_META_PATH}")

    with CATEGORIES_META_PATH.open("r", encoding="utf-8") as f:
        data = json.load(f)

    categories = data.get("categories", [])
    if not categories:
        raise ValueError("categories_meta.json no tiene clave 'categories' o está vacía")

    return categories


def loadCategoriesAssignments():
    if not CATEGORIES_CSV_PATH.exists():
        raise FileNotFoundError(f"no se encontró {CATEGORIES_CSV_PATH}")

    df = pd.read_csv(CATEGORIES_CSV_PATH)

    expected_cols = {"pdf_path", "pdf_filename", "category", "updated_at", "missing"}
    missing_cols = expected_cols - set(df.columns)
    if missing_cols:
        raise ValueError(f"faltan columnas en categories.csv: {missing_cols}")

    return df


def createCategoryFolders(categories):
    paths = [TRAIN_ROOT] + [TRAIN_ROOT / cat for cat in categories]
    ensureDirs(paths)
    return {cat: TRAIN_ROOT / cat for cat in categories}


def moveFile(src_path, dst_dir):
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst_path = dst_dir / src_path.name

    i = 1
    while dst_path.exists():
        dst_path = dst_dir / f"{src_path.stem}__{i}{src_path.suffix}"
        i += 1

    shutil.move(str(src_path), str(dst_path))
    return dst_path


def buildTrainSplit():
    categories = loadCategoriesMeta()
    df = loadCategoriesAssignments()

    category_dirs = createCategoryFolders(categories)

    manifest_rows = []
    skipped_rows = []

    df_filtered = df.copy()
    df_filtered = df_filtered[df_filtered["missing"] == 0]

    for _, row in df_filtered.iterrows():
        pdf_path_str = row["pdf_path"]
        category = row["category"]

        if category not in category_dirs:
            skipped_rows.append(
                {
                    "reason": "categoria_no_en_meta",
                    "pdf_path": pdf_path_str,
                    "category": category,
                }
            )
            continue

        src_path = Path(pdf_path_str)

        if not src_path.exists():
            skipped_rows.append(
                {
                    "reason": "archivo_no_encontrado",
                    "pdf_path": pdf_path_str,
                    "category": category,
                }
            )
            continue

        dst_dir = category_dirs[category]
        dst_path = moveFile(src_path, dst_dir)

        manifest_rows.append(
            {
                "pdf_filename": row["pdf_filename"],
                "original_pdf_path": pdf_path_str,
                "category": category,
                "split": "train",
                "new_pdf_path": str(dst_path),
                "updated_at": row.get("updated_at", ""),
            }
        )

    if not manifest_rows:
        print("no se movió ningún archivo, revisa el csv y los filtros")
        return

    manifest_df = pd.DataFrame(manifest_rows)
    toCsv(manifest_df, TRAIN_MANIFEST_PATH, overwrite=True)

    counts_df = (
        manifest_df.groupby("category")
        .size()
        .reset_index(name="file_count")
        .sort_values("category")
    )
    toCsv(counts_df, TRAIN_COUNTS_PATH, overwrite=True)

    print("train split listo ✓")
    print(f"- manifest por archivo: {TRAIN_MANIFEST_PATH}")
    print(f"- conteo por categoria: {TRAIN_COUNTS_PATH}")

    if skipped_rows:
        skipped_df = pd.DataFrame(skipped_rows)
        skipped_path = PROC_DIR / "train_skipped.csv"
        toCsv(skipped_df, skipped_path, overwrite=True)
        print(f"- filas omitidas registradas en: {skipped_path}")


def main():
    ensureDirs([SPLITS_DIR, TRAIN_ROOT])
    buildTrainSplit()


if __name__ == "__main__":
    main()
