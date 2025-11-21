from transformers.utils import logging

def quietHf():
    # baja el nivel de logs de HF
    logging.set_verbosity_error()
    logging.disable_default_handler()
    logging.enable_explicit_format()

    # desactiva logs ruidosos de módulos específicos
    noisy_modules = [
        "transformers",
        "transformers.tokenization_utils_base",
        "transformers.modeling_utils",
        "transformers.image_processing_utils",
    ]

    for name in noisy_modules:
        logging.get_logger(name).setLevel(logging.ERROR)
