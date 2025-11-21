import argparse

from src.budget_buddy.preprocessing.pdf_to_images import buildImagesForSplit


def main():
    ap = argparse.ArgumentParser()  # parser para los args del cli

    # split para elegir qué conjunto procesar
    ap.add_argument(
        "--split",
        choices=["train", "test"],
        default="train",
        help="split a procesar (train o test)",
    )

    # dpi alto para mejor calidad al rasterizar
    ap.add_argument(
        "--dpi",
        type=int,
        default=450,
        help="dpi para rasterizar los pdfs",
    )

    # límite pequeño útil para pruebas rápidas
    ap.add_argument(
        "--max-per-category",
        type=int,
        default=None,
        help="límite opcional de pdfs por categoría (para pruebas rápidas)",
    )

    # permitir regenerar imágenes existentes
    ap.add_argument(
        "--overwrite",
        action="store_true",
        help="si se pasa, vuelve a generar las imágenes aunque ya existan",
    )

    args = ap.parse_args()

    # delega el procesamiento a la función del módulo
    buildImagesForSplit(
        split=args.split,
        dpi=args.dpi,
        max_per_category=args.max_per_category,
        overwrite=args.overwrite,
    )


if __name__ == "__main__":
    main()
