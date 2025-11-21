import argparse
from pathlib import Path

from src.budget_buddy.ocr.trocr_finetune import trainTrocrFel


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-dir",
        type=str,
        default="models/trocr_fel_v1",
        help="directorio donde se guardará el modelo fine-tuned",
    )
    parser.add_argument(
        "--device",
        choices=["auto", "cpu", "cuda"],
        default="auto",
        help="device a usar para entrenamiento",
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=5,
        help="número de épocas de entrenamiento",
    )
    parser.add_argument(
        "--train-batch-size",
        type=int,
        default=4,
        help="batch size de entrenamiento por device",
    )
    parser.add_argument(
        "--eval-batch-size",
        type=int,
        default=4,
        help="batch size de evaluación por device",
    )
    parser.add_argument(
        "--lr",
        type=float,
        default=5e-5,
        help="learning rate",
    )
    parser.add_argument(
        "--weight-decay",
        type=float,
        default=0.01,
        help="weight decay",
    )
    parser.add_argument(
        "--warmup-ratio",
        type=float,
        default=0.1,
        help="ratio de warmup sobre steps totales",
    )
    parser.add_argument(
        "--no-fp16",
        action="store_true",
        help="desactiva fp16 aunque haya gpu",
    )
    parser.add_argument(
        "--logging-steps",
        type=int,
        default=10,
        help="cada cuántos steps loguear",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="semilla aleatoria",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir)

    trainTrocrFel(
        output_dir=str(output_dir),
        device_preference=args.device,
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.train_batch_size,
        per_device_eval_batch_size=args.eval_batch_size,
        learning_rate=args.lr,
        weight_decay=args.weight_decay,
        warmup_ratio=args.warmup_ratio,
        fp16=not args.no_fp16,
        logging_steps=args.logging_steps,
        seed=args.seed,
    )


if __name__ == "__main__":
    main()
