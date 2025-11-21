import argparse
from pathlib import Path
from src.budget_buddy.preprocessing.cleaning import unzipAll, buildManifest
from src.budget_buddy.utils.io import ensureDirs


def main():
    parser = argparse.ArgumentParser()
    # activar hash sha256 para detectar duplicados por contenido
    parser.add_argument("--hash", action="store_true", help="calcular sha256 para duplicados por contenido")
    # permitir sobrescribir csv existentes
    parser.add_argument("--overwrite", action="store_true", help="reemplazar csv si existe")
    args = parser.parse_args()

    root = Path(".")
    raw_dir = root / "data" / "raw" / "pdf"
    interim_unzip_dir = root / "data" / "interim" / "unzipped_pdfs"
    processed_dir = root / "data" / "processed"

    manifest_csv = processed_dir / "manifest_pdfs.csv"
    dup_csv = processed_dir / "manifest_duplicates.csv"

    ensureDirs([interim_unzip_dir, processed_dir])

    # descomprimir todos los zips
    unzipAll(raw_dir, interim_unzip_dir)

    # generar manifest y archivo de duplicados
    buildManifest(
        interim_unzip_dir=interim_unzip_dir,
        manifest_csv=manifest_csv,
        duplicates_csv=dup_csv,
        compute_hash=args.hash,
        overwrite=args.overwrite,
    )

    print(f"listo ✓\n- manifest: {manifest_csv}\n- duplicados: {dup_csv}")


if __name__ == "__main__":
    main()
