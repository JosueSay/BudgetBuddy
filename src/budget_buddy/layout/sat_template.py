from pathlib import Path
import yaml


ROOT = Path(".")
SAT_TEMPLATE_PATH = ROOT / "config" / "sat_template.yaml"


def loadSatTemplate(config_path: Path | None = None):
    # lee el yaml de plantilla sat
    cfg_path = config_path or SAT_TEMPLATE_PATH
    if not cfg_path.exists():
        raise FileNotFoundError(f"no se encontró {cfg_path}")

    with cfg_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if "sat_template" not in data:
        raise ValueError("el yaml no tiene clave 'sat_template'")

    tpl = data["sat_template"]
    regions = tpl.get("regions", {})
    active_regions = tpl.get("active_regions", list(regions.keys()))

    return {
        "page_size": tpl.get("page_size", {}),
        "regions": regions,
        "active_regions": active_regions,
    }


def regionToBoxPx(region_cfg: dict, img_width: int, img_height: int):
    # convierte coords normalizadas [0,1] en caja (left, top, right, bottom)
    x0 = float(region_cfg["x0"])
    x1 = float(region_cfg["x1"])
    y0 = float(region_cfg["y0"])
    y1 = float(region_cfg["y1"])

    left = int(round(x0 * img_width))
    right = int(round(x1 * img_width))
    top = int(round(y0 * img_height))
    bottom = int(round(y1 * img_height))

    return left, top, right, bottom


def getSatRegionsBoxes(img_width: int, img_height: int, config_path: Path | None = None):
    # devuelve dict region_name -> (left, top, right, bottom)
    tpl = loadSatTemplate(config_path=config_path)
    regions_cfg = tpl["regions"]
    active_regions = tpl["active_regions"]

    boxes = {}
    for name in active_regions:
        if name not in regions_cfg:
            continue
        box = regionToBoxPx(regions_cfg[name], img_width, img_height)
        boxes[name] = box

    return boxes