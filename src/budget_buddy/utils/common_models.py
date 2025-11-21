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


def loadTrocrModel(modelDir: str, device: torch.device):
    # carga modelo y processor de trocr
    processor = TrOCRProcessor.from_pretrained(modelDir)
    model = VisionEncoderDecoderModel.from_pretrained(modelDir)
    model.to(device)
    model.eval()
    return processor, model


def loadTrocrModelForExplain(modelDir: str, device: torch.device):
    # mismo loader pero habilita hidden states para xai
    processor = TrOCRProcessor.from_pretrained(modelDir)
    model = VisionEncoderDecoderModel.from_pretrained(modelDir)
    model.config.output_hidden_states = True
    model.to(device)
    model.eval()
    return processor, model
