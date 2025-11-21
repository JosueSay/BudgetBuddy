from pathlib import Path
import math
from typing import Optional

import torch
import numpy as np
from PIL import Image

import matplotlib.pyplot as plt
from transformers import TrOCRProcessor, VisionEncoderDecoderModel

from src.budget_buddy.utils.common_models import getDevice, loadTrocrModelForExplain



def loadTrocrModelForExplain(model_path_or_name: str, device: torch.device):
    # carga modelo y processor, configurado para sacar encoder outputs
    processor = TrOCRProcessor.from_pretrained(model_path_or_name)
    model = VisionEncoderDecoderModel.from_pretrained(model_path_or_name)
    model.config.output_hidden_states = True
    model.to(device)
    model.eval()
    return processor, model


def computeVisualImportanceMap(model, processor, image_path: str, device: torch.device) -> np.ndarray:
    # genera mapa simple de importancia a partir de la norma de los embeddings de visión
    img = Image.open(image_path).convert("RGB")

    inputs = processor(images=img, return_tensors="pt").to(device)
    with torch.no_grad():
        encoder_outputs = model.get_encoder()(
            inputs.pixel_values,
            output_hidden_states=True,
            return_dict=True,
        )

    last_hidden = encoder_outputs.last_hidden_state  # (1, seq_len, hidden)
    hidden = last_hidden[0]  # (seq_len, hidden)

    token_norms = torch.norm(hidden, dim=-1)  # (seq_len,)

    if token_norms.shape[0] <= 1:
        raise RuntimeError("no se pudo inferir grid de visión desde hidden_state")

    patch_tokens = token_norms[1:]
    seq_len = patch_tokens.shape[0]
    side = int(math.sqrt(seq_len))

    if side * side != seq_len:
        raise RuntimeError(f"no se pudo reconstruir grid cuadrado para seq_len={seq_len}")

    grid = patch_tokens.reshape(side, side).cpu().numpy()
    grid = grid - grid.min()
    if grid.max() > 0:
        grid = grid / grid.max()

    return grid


def saveHeatmapOverlay(
    image_path: str,
    heatmap: np.ndarray,
    output_path: str,
    alpha: float = 0.5,
):
    # guarda imagen original con heatmap superpuesto
    img = Image.open(image_path).convert("RGB")
    img_w, img_h = img.size

    heatmap_img = Image.fromarray((heatmap * 255).astype(np.uint8))
    heatmap_img = heatmap_img.resize((img_w, img_h), resample=Image.BILINEAR)

    plt.figure(figsize=(6, 8))
    plt.imshow(img)
    plt.imshow(heatmap_img, cmap="jet", alpha=alpha)
    plt.axis("off")
    plt.tight_layout()
    plt.savefig(output_path, bbox_inches="tight", pad_inches=0)
    plt.close()


def explainInvoiceImage(
    model_path_or_name: str,
    image_path: str,
    output_path: str,
    device_preference: str = "auto",
):
    device = getDevice(device_preference)

    processor, model = loadTrocrModelForExplain(model_path_or_name, device)
    heatmap = computeVisualImportanceMap(model, processor, image_path, device)
    saveHeatmapOverlay(image_path, heatmap, output_path)
    print(f"heatmap guardado en: {output_path}")
