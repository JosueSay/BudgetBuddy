from pathlib import Path
from dataclasses import dataclass
from typing import Any
from inspect import signature
from datetime import datetime
import json

import torch
from torch.utils.data import random_split
from transformers import (
    Trainer,
    TrainingArguments,
    EvalPrediction
)

from src.budget_buddy.utils.common_models import getDevice, loadTrocrModel
from src.budget_buddy.utils.logging_config import quietHf
quietHf()

from src.budget_buddy.datasets.trocr_invoice_dataset import (
    collectInvoicePairs,
    TrOcrInvoiceDataset,
)

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


def buildDatasets(
    processor,
    max_target_length: int,
    train_val_split: float,
    seed: int = 42,
):
    # arma dataset completo y lo separa en train/val
    pairs = collectInvoicePairs()
    full_dataset = TrOcrInvoiceDataset(
        processor=processor,
        pairs=pairs,
        max_target_length=max_target_length,
    )

    n_total = len(full_dataset)
    n_train = int(n_total * train_val_split)
    n_val = max(1, n_total - n_train)

    generator = torch.Generator().manual_seed(seed)
    train_dataset, val_dataset = random_split(
        full_dataset,
        lengths=[n_train, n_val],
        generator=generator,
    )

    print(f"dataset trocr fel → total={n_total}, train={n_train}, val={n_val}")
    return train_dataset, val_dataset


def collateFn(batch: list[dict[str, Any]]) -> dict[str, Any]:
    # collate para trocr con padding dinámico en labels
    # pixel_values ya viene con tamaño uniforme desde el dataset
    pixel_values = torch.stack([item["pixel_values"] for item in batch])

    labels_list = [item["labels"] for item in batch]
    max_len = max(lbl.size(0) for lbl in labels_list)

    # rellenar con -100 (token ignorado por el loss)
    padded_labels = torch.full(
        (len(labels_list), max_len),
        fill_value=-100,
        dtype=torch.long,
    )

    for i, lbl in enumerate(labels_list):
        length = lbl.size(0)
        padded_labels[i, :length] = lbl

    return {"pixel_values": pixel_values, "labels": padded_labels}


def computeMetrics(eval_pred) -> dict[str, float]:
    # eval_pred puede ser EvalPrediction o tuple(predictions, label_ids)
    if isinstance(eval_pred, EvalPrediction):
        logits = eval_pred.predictions
        labels = eval_pred.label_ids
    else:
        logits, labels = eval_pred

    # algunos modelos devuelven un tuple (logits, ...)
    if isinstance(logits, (tuple, list)):
        logits = logits[0]

    # a numpy si no lo es
    if isinstance(logits, torch.Tensor):
        logits_tensor = logits
    else:
        logits_tensor = torch.tensor(logits)

    if isinstance(labels, torch.Tensor):
        labels_tensor = labels
    else:
        labels_tensor = torch.tensor(labels)

    # predicciones: argmax por token
    preds_tensor = logits_tensor.argmax(-1)

    # ignorar tokens enmascarados con -100
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
    # guarda métricas + config en modelo y en outputs/tables
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
        },
        "train_metrics": train_metrics,
        "eval_metrics": eval_metrics,
    }

    cfg.output_dir.mkdir(parents=True, exist_ok=True)
    metrics_model_path = cfg.output_dir / "training_metrics.json"
    metrics_model_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    METRICS_ROOT.mkdir(parents=True, exist_ok=True)
    metrics_global_path = METRICS_ROOT / "trocr_fel_metrics.json"
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
) -> str:
    # orquesta finetuning de trocr sobre facturas fel
    cfg = TrocrTrainingConfig(
        output_dir=Path(output_dir),
        num_train_epochs=num_train_epochs,
        per_device_train_batch_size=per_device_train_batch_size,
        per_device_eval_batch_size=per_device_eval_batch_size,
        learning_rate=learning_rate,
        weight_decay=weight_decay,
        warmup_ratio=warmup_ratio,
        fp16=fp16,
        logging_steps=logging_steps,
        seed=seed,
    )

    cfg.output_dir.mkdir(parents=True, exist_ok=True)

    device = getDevice(device_preference)
    print(f"usando device: {device}")

    processor, model = loadTrocrModel(cfg.model_name, device)

    train_dataset, val_dataset = buildDatasets(
        processor=processor,
        max_target_length=cfg.max_target_length,
        train_val_split=cfg.train_val_split,
        seed=cfg.seed,
    )

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
