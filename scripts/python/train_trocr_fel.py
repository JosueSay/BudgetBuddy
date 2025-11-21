import argparse

from src.budget_buddy.ocr.trocr_finetune import trainTrocrFel


def main():
    parser = argparse.ArgumentParser()

    # ruta donde se guardará el modelo
    parser.add_argument(
        "--output-dir",
        type=str,
        default="models/trocr_fel_v1",
        help="directorio donde se guardará el modelo fine-tuned",
    )

    # selección automática o manual del device
    parser.add_argument(
        "--device",
        choices=["auto", "cpu", "cuda"],
        default="auto",
        help="device a usar para entrenamiento",
    )

    # número de épocas totales
    parser.add_argument(
        "--epochs",
        type=int,
        default=5,
        help="número de épocas de entrenamiento",
    )

    # batch size para entrenamiento
    parser.add_argument(
        "--train-batch-size",
        type=int,
        default=4,
        help="batch size de entrenamiento por device",
    )

    # batch size para evaluación
    parser.add_argument(
        "--eval-batch-size",
        type=int,
        default=4,
        help="batch size de evaluación por device",
    )

    # tasa de aprendizaje
    parser.add_argument(
        "--lr",
        type=float,
        default=5e-5,
        help="learning rate",
    )

    # regularización ligera
    parser.add_argument(
        "--weight-decay",
        type=float,
        default=0.01,
        help="weight decay",
    )

    # proporción de warmup
    parser.add_argument(
        "--warmup-ratio",
        type=float,
        default=0.1,
        help="ratio de warmup sobre steps totales",
    )

    # desactivar fp16 si se requiere
    parser.add_argument(
        "--no-fp16",
        action="store_true",
        help="desactiva fp16 aunque haya gpu",
    )

    # frecuencia del logging
    parser.add_argument(
        "--logging-steps",
        type=int,
        default=10,
        help="cada cuántos steps loguear",
    )

    # fijar semilla para reproducibilidad
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="semilla aleatoria",
    )

    # modo de recorte o vista de imagen
    parser.add_argument(
        "--image-mode",
        choices=["full", "sat-header"],
        default="full",
        help="modo de imagen para entrenamiento: 'full' (página completa) o 'sat-header' (solo encabezado)",
    )

    # aplicar augmentación ligera
    parser.add_argument(
        "--use-augment",
        action="store_true",
        help="aplica data augmentation ligero sobre las imágenes de entrenamiento",
    )

    args = parser.parse_args()

    # se inicia el fine-tuning con los parámetros configurados
    trainTrocrFel(
        output_dir=args.output_dir,
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
        image_mode=args.image_mode,
        use_augment=args.use_augment,
    )


if __name__ == "__main__":
    main()
