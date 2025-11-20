import argparse
import json
import shutil
from datetime import datetime
from pathlib import Path

import pandas as pd

from src.budget_buddy.utils.io import ensureDirs, toCsv
from src.budget_buddy.preprocessing.cleaning import unzipAll


ROOT = Path(".")
PROC_DIR = ROOT / "data" / "processed"
SPLITS_DIR = ROOT / "data" / "splits"
TRAIN_ROOT = SPLITS_DIR / "train"
TRAIN_TRASH_ROOT = SPLITS_DIR / ".trash"

XML_RAW_DIR = ROOT / "data" / "raw" / "xml"
XML_UNZIPPED_DIR = ROOT / "data" / "interim" / "unzipped_xml"

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


def buildXmlIndex():
    """
    Indexa los XML en data/interim/unzipped_xml por nombre base (stem).
    Ej.: ABC123.pdf ↔ ABC123.xml
    """
    index = {}
    if not XML_UNZIPPED_DIR.exists():
        return index

    for xml_path in XML_UNZIPPED_DIR.rglob("*.xml"):
        stem = xml_path.stem
        # si hay duplicados, nos quedamos con el primero (se puede refinar luego)
        if stem not in index:
            index[stem] = xml_path
    return index


def buildTrainSplit():
    categories = loadCategoriesMeta()
    df = loadCategoriesAssignments()

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = TRAIN_TRASH_ROOT / f"run_{ts}"
    backupTrainArtifacts(run_dir)

    category_dirs = createCategoryFolders(categories)

    manifest_rows = []
    skipped_rows = []

    # 1) filtrar PDFs que sí existen según categories.csv (missing == 0)
    df_filtered = df.copy()
    df_filtered = df_filtered[df_filtered["missing"] == 0]

    # 2) preparar XML: unzip y build index
    if XML_RAW_DIR.exists():
        ensureDirs([XML_UNZIPPED_DIR])
        # descomprime todos los zips de xml a /data/interim/unzipped_xml
        unzipAll(XML_RAW_DIR, XML_UNZIPPED_DIR)

    xml_index = buildXmlIndex()

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

        # base pdf: solo pasa a train si existe XML con el mismo stem
        stem = src_path.stem
        xml_path = xml_index.get(stem)

        if xml_path is None:
            skipped_rows.append(
                {
                    "reason": "xml_no_encontrado",
                    "pdf_path": pdf_path_str,
                    "category": category,
                }
            )
            continue

        dst_dir = category_dirs[category]

        # mover PDF
        dst_pdf_path = moveFile(src_path, dst_dir)

        # mover XML asociado
        if not xml_path.exists():
            # por si el xml fue borrado entre el índice y ahora
            skipped_rows.append(
                {
                    "reason": "xml_desaparecido",
                    "pdf_path": pdf_path_str,
                    "category": category,
                    "xml_expected": str(xml_path),
                }
            )
            continue

        dst_xml_path = moveFile(xml_path, dst_dir)

        manifest_rows.append(
            {
                "pdf_filename": row["pdf_filename"],
                "original_pdf_path": pdf_path_str,
                "original_xml_path": str(xml_path),
                "category": category,
                "split": "train",
                "new_pdf_path": str(dst_pdf_path),
                "new_xml_path": str(dst_xml_path),
                "updated_at": row.get("updated_at", ""),
            }
        )

    if not manifest_rows:
        print("no se movió ningún archivo, revisa el csv, XML y los filtros")
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

        # también caminos para xml (pueden no existir en corridas viejas)
        new_xml_path_str = row.get("new_xml_path", "")
        orig_xml_path_str = row.get("original_xml_path", "")

        # restaurar PDF
        if new_path_str and orig_path_str:
            src = Path(new_path_str)
            dst = Path(orig_path_str)

            if src.exists():
                dst.parent.mkdir(parents=True, exist_ok=True)
                final_dst = dst

                i = 1
                while final_dst.exists():
                    final_dst = dst.with_name(f"{dst.stem}__restored{i}{dst.suffix}")
                    i += 1

                shutil.move(str(src), str(final_dst))
                print(f"+ restaurado PDF: {final_dst}")
                restored += 1
            else:
                print(f"- no encontrado en split (PDF, saltando): {src}")
                skipped += 1

        # restaurar XML (si hay info en el log)
        if new_xml_path_str and orig_xml_path_str:
            src_xml = Path(new_xml_path_str)
            dst_xml = Path(orig_xml_path_str)

            if src_xml.exists():
                dst_xml.parent.mkdir(parents=True, exist_ok=True)
                final_dst_xml = dst_xml

                i = 1
                while final_dst_xml.exists():
                    final_dst_xml = dst_xml.with_name(f"{dst_xml.stem}__restored{i}{dst_xml.suffix}")
                    i += 1

                shutil.move(str(src_xml), str(final_dst_xml))
                print(f"+ restaurado XML: {final_dst_xml}")
            else:
                print(f"- no encontrado en split (XML, saltando): {src_xml}")

    print(f"\nresumen undo → restaurados (PDF): {restored}, omitidos: {skipped}")

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
