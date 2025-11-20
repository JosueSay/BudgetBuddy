from pathlib import Path
import argparse, re, shutil, sys
from datetime import datetime
import pandas as pd

from src.budget_buddy.preprocessing.cleaning import scanPdfs, markDuplicatesByName, addHashes
from src.budget_buddy.utils.io import toCsv

# rutas base
ROOT = Path(".")
INTERIM_UNZIPPED = ROOT / "data" / "interim" / "unzipped_pdfs"
PROC_DIR = ROOT / "data" / "processed"
MANIFEST = PROC_DIR / "manifest_pdfs.csv"
DUPS = PROC_DIR / "manifest_duplicates.csv"
TRASH_ROOT = ROOT / "data" / "interim" / ".trash"


def backupManifests(trash_run_dir: Path):
    # guarda copia de los manifests actuales en la carpeta de papelera antes de borrar
    trash_run_dir.mkdir(parents=True, exist_ok=True)
    if MANIFEST.exists():
        shutil.copy2(MANIFEST, trash_run_dir / "manifest_pdfs.bak.csv")
    if DUPS.exists():
        shutil.copy2(DUPS, trash_run_dir / "manifest_duplicates.bak.csv")

def restoreManifestsFromBackup(trash_run_dir: Path):
    # restaura los manifests desde los .bak guardados en la corrida de papelera
    bak_manifest = trash_run_dir / "manifest_pdfs.bak.csv"
    bak_dups = trash_run_dir / "manifest_duplicates.bak.csv"
    if bak_manifest.exists():
        shutil.copy2(bak_manifest, MANIFEST)
    if bak_dups.exists():
        shutil.copy2(bak_dups, DUPS)


# util simple de salida
def die(msg, code=1):
    print(f"error: {msg}")
    sys.exit(code)

# mueve archivo a papelera con timestamp
def moveToTrash(src_path: Path, trash_run_dir: Path):
    # conserva estructura plana con nombre único
    if not src_path.exists():
        return None
    trash_run_dir.mkdir(parents=True, exist_ok=True)
    dst = trash_run_dir / src_path.name
    # evita colisión de nombre
    i = 1
    while dst.exists():
        dst = trash_run_dir / f"{src_path.stem}__{i}{src_path.suffix}"
        i += 1
    shutil.move(str(src_path), str(dst))
    return dst

# imprime tabla compacta del grupo
def printGroup(group_df: pd.DataFrame, group_key: str, by: str):
    print("\n" + "=" * 60)
    print(f"grupo: {group_key}  |  criterio: {by}")
    print("-" * 60)
    for idx, row in group_df.reset_index(drop=True).iterrows():
        print(f"[{idx}] zip={row['zip_root']}  year={row['year']}  block={row['block']}  size={row['size_bytes']}  path={row['pdf_path']}")
    print("=" * 60)

# refresca manifests re-escaneando el disco (más fiable)
def refreshManifests(compute_hash: bool):
    df = scanPdfs(INTERIM_UNZIPPED)
    df = markDuplicatesByName(df)
    if compute_hash:
        df = addHashes(df)
    toCsv(df, MANIFEST, overwrite=True)

    # recomputa duplicados a partir del manifest actualizado
    keep_cols = ["pdf_filename","zip_root","year","block","size_bytes","pdf_path","first_seen_zip","is_name_duplicate"]
    if compute_hash and "sha256" in df.columns:
        keep_cols += ["sha256","is_hash_duplicate"]
        dups = df[(df["is_name_duplicate"]) | (df["hash_count"] > 1)].copy()
    else:
        dups = df[df["is_name_duplicate"]].copy()
    dups = dups[keep_cols].sort_values(["pdf_filename","year","block"])
    toCsv(dups, DUPS, overwrite=True)

def loadDuplicates(by: str, pattern: str | None):
    if not DUPS.exists():
        die("no existe data/processed/manifest_duplicates.csv; corre preprocess primero")
    df = pd.read_csv(DUPS)
    # filtra criterio
    if by == "hash":
        if "sha256" not in df.columns:
            die("el manifest no tiene sha256; corre preprocess con --hash")
        df = df[df.get("is_hash_duplicate", False) == True].copy()
        key_col = "sha256"
    else:
        df = df[df["is_name_duplicate"] == True].copy()
        key_col = "pdf_filename"

    if pattern:
        rgx = re.compile(pattern)
        df = df[df[key_col].astype(str).str.contains(rgx)]

    if df.empty:
        print("no hay duplicados para resolver con el criterio dado")
        return key_col, {}
    groups = {k: g.copy() for k, g in df.groupby(key_col)}
    return key_col, groups

def interactiveResolve(by: str, groups: dict, apply: bool, compute_hash: bool):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    trash_run_dir = TRASH_ROOT / f"run_{ts}"
    log_rows = []

    keys = list(groups.keys())
    while True:
        # lista grupos disponibles
        print("\n=== grupos disponibles ===")
        for i, k in enumerate(keys):
            print(f"[{i}] {k}  (n={len(groups[k])})")
        print("[x] salir")

        choice = input("elige índice de grupo o 'x': ").strip()
        if choice.lower() == "x":
            break
        if not choice.isdigit() or int(choice) not in range(len(keys)):
            print("entrada inválida")
            continue

        gkey = keys[int(choice)]
        gdf = groups[gkey]
        printGroup(gdf, gkey, by)

        keep = input("elige índice a CONSERVAR (o 'c' para cancelar este grupo): ").strip()
        if keep.lower() == "c":
            print("cancelado este grupo")
            continue
        if not keep.isdigit() or int(keep) not in range(len(gdf)):
            print("entrada inválida")
            continue

        keep_idx = int(keep)
        keep_row = gdf.reset_index(drop=True).iloc[keep_idx]
        print(f"se conservará: {keep_row['pdf_path']}")
        confirm = input("confirmar? (y/n): ").strip().lower()
        if confirm != "y":
            print("no se hizo nada")
            continue


        # elimina (mueve a papelera) los demás
        to_drop = gdf.reset_index(drop=True).drop(index=keep_idx)

        # backup de manifests una sola vez (antes del primer movimiento real)
        if apply and not (trash_run_dir / "manifest_pdfs.bak.csv").exists():
            backupManifests(trash_run_dir)

        for _, r in to_drop.iterrows():
            src = Path(r["pdf_path"])
            if apply:
                dst = moveToTrash(src, trash_run_dir)
            else:
                dst = None

            log_rows.append({
                "action": "trash" if apply else "dry-run",
                "criterion": by,
                "group_key": gkey,
                "kept_pdf": keep_row["pdf_path"],
                "removed_pdf_original_path": r["pdf_path"],   # ← path original para undo exacto
                "removed_pdf_trash_path": str(dst) if dst else "",
                "from_zip": r["zip_root"],
                "year": r.get("year", ""),
                "block": r.get("block", ""),
                "size_bytes": r.get("size_bytes", "")
            })
            print(f"- {'mover a papelera' if apply else 'simular'}: {r['pdf_path']}")

        del groups[gkey]
        keys = list(groups.keys())

    # guarda log y refresca/actualiza manifests
    if log_rows:
        trash_run_dir.mkdir(parents=True, exist_ok=True)
        log_csv = trash_run_dir / "deletion_log.csv"
        pd.DataFrame(log_rows).to_csv(log_csv, index=False)
        print(f"\nlog guardado en: {log_csv}")

    if apply and log_rows:
        print("\nrefrescando manifests…")
        refreshManifests(compute_hash=compute_hash)
        print(f"actualizado: {MANIFEST}\nactualizado: {DUPS}")


def undoRun(run_dir: Path):
    if not run_dir.exists():
        die("no existe el directorio de papelera indicado")

    log_csv = run_dir / "deletion_log.csv"
    if not log_csv.exists():
        die("no existe deletion_log.csv en la corrida indicada")

    df = pd.read_csv(log_csv)
    if df.empty:
        print("no hay movimientos registrados para deshacer")
        return

    restored, skipped = 0, 0
    for _, row in df.iterrows():
        trash_path = row.get("removed_pdf_trash_path", "")
        orig_path = row.get("removed_pdf_original_path", "")
        if not trash_path or not orig_path:
            skipped += 1
            continue

        src = Path(trash_path)
        dst = Path(orig_path)

        if not src.exists():
            print(f"- no encontrado en papelera (saltando): {src}")
            skipped += 1
            continue

        dst.parent.mkdir(parents=True, exist_ok=True)
        # si ya existe en destino (alguien lo restauró a mano), no pisamos
        final_dst = dst
        i = 1
        while final_dst.exists():
            final_dst = dst.with_name(f"{dst.stem}__restored{i}{dst.suffix}")
            i += 1

        shutil.move(str(src), str(final_dst))
        print(f"+ restaurado: {final_dst}")
        restored += 1

    print(f"\nresumen undo → restaurados: {restored}, omitidos: {skipped}")

    # restaurar manifests desde backup (si existen)
    restoreManifestsFromBackup(run_dir)
    print(f"manifests restaurados desde backup (si estaban disponibles):\n- {MANIFEST}\n- {DUPS}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--by", choices=["name","hash"], default="name", help="criterio de duplicado")
    ap.add_argument("--filter", type=str, default=None, help="regex para filtrar grupos (ej. parte del nombre/sha)")
    ap.add_argument("--apply", action="store_true", help="aplica cambios (sin esto es dry-run)")
    ap.add_argument("--undo", type=str, help="ruta a data/interim/.trash/run_YYYYmmdd_HHMMSS para revertir")
    args = ap.parse_args()

    if args.undo:
        undoRun(Path(args.undo))
        return

    key_col, groups = loadDuplicates(by=args.by, pattern=args.filter)
    if not groups:
        return

    print("\nmodo:", "APLICAR" if args.apply else "dry-run (sin cambios)")
    interactiveResolve(by=args.by, groups=groups, apply=args.apply, compute_hash=(args.by=="hash"))

if __name__ == "__main__":
    main()
