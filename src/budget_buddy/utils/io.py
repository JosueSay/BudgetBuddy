from pathlib import Path
import hashlib
import pandas as pd

def ensureDirs(paths):
    # crea directorios si no existen
    for p in paths:
        Path(p).mkdir(parents=True, exist_ok=True)

def sha256File(path, chunk_size=1 << 20):
    # hash de archivo en bloques para evitar cargar todo en memoria
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk_size)
            if not b:
                break
            h.update(b)
    return h.hexdigest()

def toCsv(df: pd.DataFrame, path: Path, overwrite=False):
    # guarda csv respetando overwrite
    if path.exists() and not overwrite:
        raise FileExistsError(f"ya existe {path}, usa --overwrite")
    df.to_csv(path, index=False)