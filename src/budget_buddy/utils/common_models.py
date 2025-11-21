from pathlib import Path
import torch
from transformers import TrOCRProcessor, VisionEncoderDecoderModel


def getDevice(devicePreference: str = "auto") -> torch.device:
    # selecciona el device segun preferencia
    if devicePreference == "cpu":
        return torch.device("cpu")

    if devicePreference == "cuda":
        if not torch.cuda.is_available():
            raise RuntimeError("se pidió cuda pero no hay gpu disponible")
        return torch.device("cuda")

    # auto
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def loadTrocrModel(modelDir: str, device):
    p = Path(modelDir)

    # si es carpeta local sin preprocessor_config, entrar al último subdir (timestamp)
    if p.is_dir() and not (p / "preprocessor_config.json").exists():
        subdirs = [d for d in p.iterdir() if d.is_dir()]
        if subdirs:
            p = sorted(subdirs)[-1]
        modelDir = str(p)

    processor = TrOCRProcessor.from_pretrained(modelDir)
    model = VisionEncoderDecoderModel.from_pretrained(modelDir).to(device)
    return processor, model


def loadTrocrModelForExplain(modelDir: str, device: torch.device):
    # mismo loader pero habilita hidden states para xai
    processor = TrOCRProcessor.from_pretrained(modelDir)
    model = VisionEncoderDecoderModel.from_pretrained(modelDir)
    model.config.output_hidden_states = True
    model.to(device)
    model.eval()
    return processor, model
