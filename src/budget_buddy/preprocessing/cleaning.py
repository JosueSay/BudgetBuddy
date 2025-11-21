import zipfile
from pathlib import Path
import re
import pandas as pd
from tqdm import tqdm

from src.budget_buddy.utils.io import sha256File, toCsv

# regex para leer year y block desde nombre
BLOCK_RE = re.compile(r"(?P<year>\d{4})_b(?P<block>[1-6])\.zip$", re.IGNORECASE)

def unzipAll(raw_dir: Path, interim_unzip_dir: Path):
    # descomprime cada zip en carpeta propia
    zips = sorted(raw_dir.glob("*.zip"))
    for z in tqdm(zips, desc="unzip"):
        out_dir = interim_unzip_dir / z.stem
        if any(out_dir.glob("**/*")):
            continue  # ya estaba descomprimido
        out_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(z, "r") as zf:
            zf.extractall(out_dir)

def parseBlock(zip_name: str):
    # extrae year y block del nombre
    m = BLOCK_RE.search(zip_name)
    if not m:
        return None, None
    return int(m.group("year")), int(m.group("block"))

def scanPdfs(interim_unzip_dir: Path):
    # recorre todos los pdfs bajo /unzipped
    rows = []
    for zip_root in sorted(interim_unzip_dir.iterdir()):
        if not zip_root.is_dir():
            continue
        year, block = parseBlock(zip_root.name + ".zip")
        for pdf in zip_root.rglob("*.pdf"):
            rows.append({
                "zip_root": zip_root.name,
                "year": year,
                "block": block,
                "pdf_relpath": str(pdf.relative_to(zip_root)),
                "pdf_filename": pdf.name,
                "pdf_path": str(pdf),
                "size_bytes": pdf.stat().st_size,
            })
    return pd.DataFrame(rows)

def markDuplicatesByName(df: pd.DataFrame):
    # marca duplicados por nombre
    df["name_count"] = df.groupby("pdf_filename")["pdf_filename"].transform("count")
    df["is_name_duplicate"] = df["name_count"] > 1
    df["first_seen_zip"] = (
        df.sort_values(["pdf_filename", "year", "block"], na_position="last")
          .groupby("pdf_filename")["zip_root"].transform("first")
    )  # zip donde apareció primero
    return df

def addHashes(df: pd.DataFrame):
    # calcula sha256 por archivo
    hashes = []
    for path in tqdm(df["pdf_path"], desc="sha256"):
        hashes.append(sha256File(Path(path)))
    df["sha256"] = hashes
    df["hash_count"] = df.groupby("sha256")["sha256"].transform("count")
    df["is_hash_duplicate"] = df["hash_count"] > 1
    return df

def buildManifest(interim_unzip_dir: Path, manifest_csv: Path, duplicates_csv: Path,
                  compute_hash=False, overwrite=False):
    # construye manifest y reporte de duplicados
    df = scanPdfs(interim_unzip_dir)
    if df.empty:
        raise RuntimeError("no se encontraron pdfs en data/interim/unzipped")

    df = markDuplicatesByName(df)
    if compute_hash:
        df = addHashes(df)

    # guarda manifest general
    toCsv(df, manifest_csv, overwrite=overwrite)

    # crea lista reducida de duplicados
    keep_cols = [
        "pdf_filename", "zip_root", "year", "block",
        "size_bytes", "pdf_path", "first_seen_zip",
        "is_name_duplicate"
    ]
    if compute_hash:
        keep_cols += ["sha256", "is_hash_duplicate"]

    dups = df[df["is_name_duplicate"] | (df["is_hash_duplicate"] if compute_hash else False)].copy()
    dups = dups[keep_cols].sort_values(["pdf_filename", "year", "block"])
    toCsv(dups, duplicates_csv, overwrite=overwrite)
