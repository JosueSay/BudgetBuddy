from pathlib import Path
from dataclasses import dataclass
from typing import Any
from inspect import signature
from datetime import datetime
import json
import torch
from torch.utils.data import random_split
from transformers import Trainer, TrainingArguments, EvalPrediction

from src.budget_buddy.utils.common_models import getDevice, loadTrocrModel
from src.budget_buddy.utils.logging_config import quietHf
quietHf()

from src.budget_buddy.datasets.trocr_invoice_dataset import collectInvoicePairs, TrOcrInvoiceDataset

import warnings
warnings.filterwarnings("ignore")


ROOT = Path(".").resolve()
TROCR_MODEL_NAME = "qantev/trocr-base-spanish"
METRICS_ROOT = ROOT / "outputs" / "tables"


@dataclass
class TrocrTrainingConfig:
    output_dir: Path
    model_name: str = TROCR_MODEL_NAME
    max_target_length: int = 128
    train_val_split: float = 0.8
    num_train_epochs: int = 5
    per_device_train_batch_size: int = 4
    per_device_eval_batch_size: int = 4
    learning_rate: float = 5e-5
    weight_decay: float = 0.01
    warmup_ratio: float = 0.1
    fp16: bool = True
    logging_steps: int = 10
    save_strategy: str = "epoch"
    evaluation_strategy: str = "epoch"
    seed: int = 42
    push_to_hub: bool = False
    image_mode: str = "full"
    use_augment: bool = False


def buildDatasets(
    processor,
    max_target_length: int,
    train_val_split: float,
    seed: int = 42,
    image_mode: str = "full",
    use_augment: bool = False,
):
    # recolecta pares (img, texto) para el dataset
    pairs = collectInvoicePairs()

    # prepara dataset con procesamiento y augment opcional
    full_dataset = TrOcrInvoiceDataset(
        processor=processor,
        pairs=pairs,
        max_target_length=max_target_length,
        image_mode=image_mode,
        use_augment=use_augment,
    )

    n_total = len(full_dataset)
    n_train = int(n_total * train_val_split)
    n_val = max(1, n_total - n_train)

    # fija semilla para splitting reproducible
    generator = torch.Generator().manual_seed(seed)

    train_dataset, val_dataset = random_split(
        full_dataset,
        lengths=[n_train, n_val],
        generator=generator,
    )

    print(f"dataset trocr fel → total={n_total}, train={n_train}, val={n_val}")
    return train_dataset, val_dataset


def collateFn(batch: list[dict[str, Any]]) -> dict[str, Any]:
    # junta imágenes en un solo tensor
    pixel_values = torch.stack([item["pixel_values"] for item in batch])

    # obtiene longitudes reales para padding dinámico
    labels_list = [item["labels"] for item in batch]
    max_len = max(lbl.size(0) for lbl in labels_list)

    # usa -100 para ignorar posiciones en el loss
    padded_labels = torch.full(
        (len(labels_list), max_len),
        fill_value=-100,
        dtype=torch.long,
    )

    # copia cada secuencia en su fila
    for i, lbl in enumerate(labels_list):
        padded_labels[i, : lbl.size(0)] = lbl

    return {"pixel_values": pixel_values, "labels": padded_labels}


def computeMetrics(eval_pred) -> dict[str, float]:
    # normalizar entrada: puede venir como EvalPrediction o tuple
    if isinstance(eval_pred, EvalPrediction):
        logits = eval_pred.predictions
        labels = eval_pred.label_ids
    else:
        logits, labels = eval_pred

    # algunos modelos entregan logits en un tuple
    if isinstance(logits, (tuple, list)):
        logits = logits[0]

    # convertir logits a tensor si hace falta
    logits_tensor = logits if isinstance(logits, torch.Tensor) else torch.tensor(logits)

    # convertir labels a tensor si hace falta
    labels_tensor = labels if isinstance(labels, torch.Tensor) else torch.tensor(labels)

    # predicción token a token
    preds_tensor = logits_tensor.argmax(-1)

    # ignorar posiciones con -100
    mask = labels_tensor != -100
    if mask.sum() == 0:
        return {"token_accuracy": 0.0}

    correct = (preds_tensor == labels_tensor) & mask
    token_accuracy = correct.sum().float() / mask.sum().float()
    return {"token_accuracy": token_accuracy.item()}


def saveMetrics(
    cfg: TrocrTrainingConfig,
    train_metrics: dict[str, Any],
    eval_metrics: dict[str, Any],
) -> None:
    # agrupar config y métricas para guardarlas
    payload = {
        "timestamp": datetime.utcnow().isoformat(),
        "config": {
            "model_name": cfg.model_name,
            "max_target_length": cfg.max_target_length,
            "train_val_split": cfg.train_val_split,
            "num_train_epochs": cfg.num_train_epochs,
            "per_device_train_batch_size": cfg.per_device_train_batch_size,
            "per_device_eval_batch_size": cfg.per_device_eval_batch_size,
            "learning_rate": cfg.learning_rate,
            "weight_decay": cfg.weight_decay,
            "warmup_ratio": cfg.warmup_ratio,
            "fp16": cfg.fp16,
            "logging_steps": cfg.logging_steps,
            "seed": cfg.seed,
            "image_mode": cfg.image_mode,
            "use_augment": cfg.use_augment,
        },
        "train_metrics": train_metrics,
        "eval_metrics": eval_metrics,
    }

    # guardar en carpeta del modelo
    cfg.output_dir.mkdir(parents=True, exist_ok=True)
    metrics_model_path = cfg.output_dir / "training_metrics.json"
    metrics_model_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    # guardar también en tabla global
    METRICS_ROOT.mkdir(parents=True, exist_ok=True)
    run_id = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    metrics_global_path = METRICS_ROOT / f"trocr_fel_metrics_{run_id}.json"
    metrics_global_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print(f"métricas guardadas en:\n- {metrics_model_path}\n- {metrics_global_path}")


def trainTrocrFel(
    output_dir: str,
    device_preference: str = "auto",
    num_train_epochs: int = 5,
    per_device_train_batch_size: int = 4,
    per_device_eval_batch_size: int = 4,
    learning_rate: float = 5e-5,
    weight_decay: float = 0.01,
    warmup_ratio: float = 0.1,
    fp16: bool = True,
    logging_steps: int = 10,
    seed: int = 42,
    image_mode: str = "full",
    use_augment: bool = False,
) -> str:

    run_id = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    unique_output_dir = Path(output_dir) / run_id

    cfg = TrocrTrainingConfig(
        output_dir=unique_output_dir,
        num_train_epochs=num_train_epochs,
        per_device_train_batch_size=per_device_train_batch_size,
        per_device_eval_batch_size=per_device_eval_batch_size,
        learning_rate=learning_rate,
        weight_decay=weight_decay,
        warmup_ratio=warmup_ratio,
        fp16=fp16,
        logging_steps=logging_steps,
        seed=seed,
        image_mode=image_mode,
        use_augment=use_augment,
    )

    # asegurar directorio de salida
    cfg.output_dir.mkdir(parents=True, exist_ok=True)

    device = getDevice(device_preference)
    print(f"usando device: {device}")

    processor, model = loadTrocrModel(cfg.model_name, device)

    train_dataset, val_dataset = buildDatasets(
        processor=processor,
        max_target_length=cfg.max_target_length,
        train_val_split=cfg.train_val_split,
        seed=cfg.seed,
        image_mode=cfg.image_mode,
        use_augment=cfg.use_augment,  # habilitar augment si toca
    )

    # preparar kwargs compatibles con TrainingArguments
    base_kwargs = {
        "output_dir": str(cfg.output_dir),
        "num_train_epochs": cfg.num_train_epochs,
        "per_device_train_batch_size": cfg.per_device_train_batch_size,
        "per_device_eval_batch_size": cfg.per_device_eval_batch_size,
        "learning_rate": cfg.learning_rate,
        "weight_decay": cfg.weight_decay,
        "logging_steps": cfg.logging_steps,
        "save_strategy": cfg.save_strategy,
        "evaluation_strategy": cfg.evaluation_strategy,
        "warmup_ratio": cfg.warmup_ratio,
        "fp16": cfg.fp16 and (device.type == "cuda"),
        "seed": cfg.seed,
        "remove_unused_columns": False,
        "save_total_limit": 2,
        "report_to": [],
    }

    # filtrar solo args válidos
    ta_sig = signature(TrainingArguments.__init__)
    valid_keys = set(ta_sig.parameters.keys())
    filtered_kwargs = {k: v for k, v in base_kwargs.items() if k in valid_keys}

    training_args = TrainingArguments(**filtered_kwargs)

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        data_collator=collateFn,
        compute_metrics=computeMetrics,
    )

    print("iniciando entrenamiento trocr fel…")
    train_result = trainer.train()

    train_metrics = train_result.metrics if hasattr(train_result, "metrics") else {}
    print("evaluando modelo en validación…")
    eval_metrics = trainer.evaluate()
    print("métricas de validación:", eval_metrics)

    print("guardando modelo y processor fine-tuned…")
    model.save_pretrained(str(cfg.output_dir))
    processor.save_pretrained(str(cfg.output_dir))

    saveMetrics(cfg, train_metrics, eval_metrics)

    return str(cfg.output_dir)
