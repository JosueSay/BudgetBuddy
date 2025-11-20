from fastapi import FastAPI, Request, HTTPException, Form
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader, select_autoescape
from pathlib import Path
from datetime import datetime
import pandas as pd
import json
import urllib.parse
from fastapi import FastAPI, Request, HTTPException, Form
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader, select_autoescape

# rutas base
ROOT = Path("/app")
DATA = ROOT / "data"
PROCESSED = DATA / "processed"
INTERIM_UNZIPPED = DATA / "interim" / "unzipped_pdfs"
MANIFEST = PROCESSED / "manifest_pdfs.csv"
CATS = PROCESSED / "categories.csv"
CATS_META = PROCESSED / "categories_meta.json"

app = FastAPI()

# static + templates
BASE_DIR = Path(__file__).parent
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
env = Environment(
    loader=FileSystemLoader(str(BASE_DIR / "templates")),
    autoescape=select_autoescape(["html", "xml"])
)

# helpers de IO
def readManifest():
    if not MANIFEST.exists():
        return pd.DataFrame(columns=[
            "pdf_filename","zip_root","year","block","size_bytes","pdf_path","first_seen_zip","is_name_duplicate"
        ])
    return pd.read_csv(MANIFEST)

def readCats():
    if not CATS.exists():
        return pd.DataFrame(columns=["pdf_path","pdf_filename","category","updated_at","missing"])
    return pd.read_csv(CATS)

def writeCats(df: pd.DataFrame):
    CATS.parent.mkdir(parents=True, exist_ok=True)
    tmp = CATS.with_suffix(".csv.tmp")
    df.to_csv(tmp, index=False)
    tmp.replace(CATS)

def readCatsMeta():
    if not CATS_META.exists():
        return {"categories": []}
    with open(CATS_META, "r", encoding="utf-8") as f:
        return json.load(f)

def writeCatsMeta(obj):
    CATS_META.parent.mkdir(parents=True, exist_ok=True)
    tmp = CATS_META.with_suffix(".json.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    tmp.replace(CATS_META)

def ensureCategory(name: str):
    meta = readCatsMeta()
    if name not in meta["categories"]:
        meta["categories"].append(name)
        writeCatsMeta(meta)

def fileExists(rel_path: str) -> bool:
    return (ROOT / rel_path).exists()

# vistas
@app.get("/", response_class=HTMLResponse)
def index(request: Request, only: str | None = None, q: str | None = None, cat: str | None = None):
    m = readManifest()
    c = readCats()

    merged = m.merge(c[["pdf_path","category","missing"]], on="pdf_path", how="left")
    merged["classified"] = merged["category"].notna()
    merged["missing"] = merged["missing"].fillna(0).astype(int)

    if q:
        ql = q.lower()
        merged = merged[merged["pdf_filename"].str.lower().str.contains(ql, na=False)]
    if only == "unclassified":
        merged = merged[~merged["classified"]]
    elif only == "classified":
        merged = merged[merged["classified"]]
    if cat:
        merged = merged[merged["category"] == cat]

    merged = merged.sort_values(["classified","pdf_filename"]).reset_index(drop=True)

    cats_meta = readCatsMeta()
    categories = sorted(cats_meta.get("categories", []), key=str.lower)

    tpl = env.get_template("index.html")
    return tpl.render(
        rows=merged.to_dict(orient="records"),
        categories=categories,
        q=q or "",
        only=only or "",
        cat=cat or ""
    )


@app.get("/pdf")
def serve_pdf(path: str):
    # path relativo a /app (ej. data/interim/unzipped/2023_b1/xxx.pdf)
    safe = Path(urllib.parse.unquote(path))
    full = ROOT / safe
    if not full.exists():
        raise HTTPException(status_code=404, detail="pdf no disponible en este host")
    # devolver como 'inline' para que el navegador lo renderice en el iframe
    return FileResponse(
        str(full),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{full.name}"'}
    )

# asignación de categorías
@app.post("/assign")
def assign_category(pdf_path: str = Form(...), category: str = Form(...)):
    if not category.strip():
        raise HTTPException(status_code=400, detail="categoria vacia")
    now = datetime.utcnow().isoformat()
    c = readCats()
    exists = fileExists(pdf_path)
    if (c["pdf_path"] == pdf_path).any():
        c.loc[c["pdf_path"] == pdf_path, ["category","updated_at","missing"]] = [category, now, 0 if exists else 1]
    else:
        c = pd.concat([c, pd.DataFrame([{
            "pdf_path": pdf_path,
            "pdf_filename": Path(pdf_path).name,
            "category": category,
            "updated_at": now,
            "missing": 0 if exists else 1
        }])], ignore_index=True)
    writeCats(c)
    ensureCategory(category)
    return RedirectResponse(url="/", status_code=303)

@app.post("/unassign")
def unassign_category(pdf_path: str = Form(...)):
    c = readCats()
    if (c["pdf_path"] == pdf_path).any():
        c.loc[c["pdf_path"] == pdf_path, ["category","updated_at"]] = [None, datetime.utcnow().isoformat()]
        writeCats(c)
    return RedirectResponse(url="/", status_code=303)

# gestión de catálogo de categorías
@app.post("/category/create")
def create_category(name: str = Form(...)):
    name = name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="nombre vacio")
    meta = readCatsMeta()
    if name not in meta["categories"]:
        meta["categories"].append(name)
        writeCatsMeta(meta)
    return RedirectResponse(url="/", status_code=303)

@app.post("/category/rename")
def rename_category(old: str = Form(...), new: str = Form(...)):
    old, new = old.strip(), new.strip()
    if not old or not new:
        raise HTTPException(status_code=400, detail="parametros invalidos")
    meta = readCatsMeta()
    if old in meta["categories"]:
        meta["categories"] = [new if x == old else x for x in meta["categories"]]
        writeCatsMeta(meta)
    c = readCats()
    if not c.empty:
        c.loc[c["category"] == old, "category"] = new
        writeCats(c)
    return RedirectResponse(url="/", status_code=303)

@app.post("/category/delete")
def delete_category(name: str = Form(...)):
    name = name.strip()
    meta = readCatsMeta()
    if name in meta["categories"]:
        meta["categories"] = [x for x in meta["categories"] if x != name]
        writeCatsMeta(meta)
    # no borramos asignaciones; solo las dejamos sin categoría
    c = readCats()
    if not c.empty:
        mask = c["category"] == name
        if mask.any():
            c.loc[mask, ["category","updated_at"]] = [None, datetime.utcnow().isoformat()]
            writeCats(c)
    return RedirectResponse(url="/", status_code=303)
