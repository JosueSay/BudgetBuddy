import argparse
import json
import shutil
from datetime import datetime
from pathlib import Path

import pandas as pd

from src.budget_buddy.utils.io import ensureDirs, toCsv


ROOT = Path(".")
PROC_DIR = ROOT / "data" / "processed"
SPLITS_DIR = ROOT / "data" / "splits"
TRAIN_ROOT = SPLITS_DIR / "train"
TRAIN_TRASH_ROOT = SPLITS_DIR / ".trash"

CATEGORIES_META_PATH = PROC_DIR / "categories_meta.json"
CATEGORIES_CSV_PATH = PROC_DIR / "categories.csv"

TRAIN_MANIFEST_PATH = PROC_DIR / "train_manifest.csv"
TRAIN_COUNTS_PATH = PROC_DIR / "train_counts.csv"
TRAIN_SKIPPED_PATH = PROC_DIR / "train_skipped.csv"

RUN_LOG_NAME = "train_split_log.csv"
RUN_MANIFEST_BAK = "train_manifest.bak.csv"
RUN_COUNTS_BAK = "train_counts.bak.csv"
RUN_SKIPPED_BAK = "train_skipped.bak.csv"


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
    # mueve archivo a la carpeta de categoria evitando colisiones
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst_path = dst_dir / src_path.name

    i = 1
    while dst_path.exists():
        dst_path = dst_dir / f"{src_path.stem}__{i}{src_path.suffix}"
        i += 1

    shutil.move(str(src_path), str(dst_path))
    return dst_path


def backupTrainArtifacts(run_dir: Path):
    # guarda backup de los csv de train para poder deshacer
    run_dir.mkdir(parents=True, exist_ok=True)
    if TRAIN_MANIFEST_PATH.exists():
        shutil.copy2(TRAIN_MANIFEST_PATH, run_dir / RUN_MANIFEST_BAK)
    if TRAIN_COUNTS_PATH.exists():
        shutil.copy2(TRAIN_COUNTS_PATH, run_dir / RUN_COUNTS_BAK)
    if TRAIN_SKIPPED_PATH.exists():
        shutil.copy2(TRAIN_SKIPPED_PATH, run_dir / RUN_SKIPPED_BAK)


def restoreTrainArtifactsFromBackup(run_dir: Path):
    # restaura los csv de train desde los backups de la corrida
    bak_manifest = run_dir / RUN_MANIFEST_BAK
    bak_counts = run_dir / RUN_COUNTS_BAK
    bak_skipped = run_dir / RUN_SKIPPED_BAK

    if bak_manifest.exists():
        shutil.copy2(bak_manifest, TRAIN_MANIFEST_PATH)
    if bak_counts.exists():
        shutil.copy2(bak_counts, TRAIN_COUNTS_PATH)
    if bak_skipped.exists():
        shutil.copy2(bak_skipped, TRAIN_SKIPPED_PATH)


def buildTrainSplit():
    categories = loadCategoriesMeta()
    df = loadCategoriesAssignments()

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = TRAIN_TRASH_ROOT / f"run_{ts}"
    backupTrainArtifacts(run_dir)

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

    if skipped_rows:
        skipped_df = pd.DataFrame(skipped_rows)
        toCsv(skipped_df, TRAIN_SKIPPED_PATH, overwrite=True)

    # guarda log de la corrida en el run_dir para poder hacer undo
    run_dir.mkdir(parents=True, exist_ok=True)
    log_path = run_dir / RUN_LOG_NAME
    manifest_df.to_csv(log_path, index=False)

    print("train split listo ✓")
    print(f"- manifest por archivo: {TRAIN_MANIFEST_PATH}")
    print(f"- conteo por categoria: {TRAIN_COUNTS_PATH}")
    if skipped_rows:
        print(f"- filas omitidas registradas en: {TRAIN_SKIPPED_PATH}")
    print(f"- log de esta corrida: {log_path}")


def undoRun(run_dir: Path):
    if not run_dir.exists():
        print("error: no existe el directorio de corrida indicado")
        return

    log_path = run_dir / RUN_LOG_NAME
    if not log_path.exists():
        print("error: no se encontró el log de movimientos en la corrida indicada")
        return

    df = pd.read_csv(log_path)
    if df.empty:
        print("no hay movimientos registrados para deshacer")
        return

    restored, skipped = 0, 0
    for _, row in df.iterrows():
        new_path_str = row.get("new_pdf_path", "")
        orig_path_str = row.get("original_pdf_path", "")

        if not new_path_str or not orig_path_str:
            skipped += 1
            continue

        src = Path(new_path_str)
        dst = Path(orig_path_str)

        if not src.exists():
            print(f"- no encontrado en split (saltando): {src}")
            skipped += 1
            continue

        dst.parent.mkdir(parents=True, exist_ok=True)
        final_dst = dst

        i = 1
        while final_dst.exists():
            final_dst = dst.with_name(f"{dst.stem}__restored{i}{dst.suffix}")
            i += 1

        shutil.move(str(src), str(final_dst))
        print(f"+ restaurado: {final_dst}")
        restored += 1

    print(f"\nresumen undo → restaurados: {restored}, omitidos: {skipped}")

    restoreTrainArtifactsFromBackup(run_dir)
    print(
        "csv de train restaurados desde backup (si estaban disponibles):\n"
        f"- {TRAIN_MANIFEST_PATH}\n"
        f"- {TRAIN_COUNTS_PATH}\n"
        f"- {TRAIN_SKIPPED_PATH}"
    )

    # intento de limpiar carpetas de categorias vacías
    if TRAIN_ROOT.exists():
        for cat_dir in TRAIN_ROOT.iterdir():
            if cat_dir.is_dir():
                try:
                    next(cat_dir.iterdir())
                except StopIteration:
                    try:
                        cat_dir.rmdir()
                    except OSError:
                        pass


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--undo",
        type=str,
        help="ruta a data/splits/.trash/run_YYYYmmdd_HHMMSS para revertir",
    )
    args = parser.parse_args()

    ensureDirs([SPLITS_DIR, TRAIN_ROOT, TRAIN_TRASH_ROOT])

    if args.undo:
        undoRun(Path(args.undo))
        return

    buildTrainSplit()


if __name__ == "__main__":
    main()
