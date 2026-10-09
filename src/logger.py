import logging
from pathlib import Path


def get_logger():
    """
    Create and return the ETL pipeline logger.
    """

    project_dir = Path(__file__).resolve().parent.parent
    logs_dir = project_dir / "logs"

    logs_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    log_file = logs_dir / "pipeline.log"

    logger = logging.getLogger(
        "api_sales_etl"
    )

    logger.setLevel(
        logging.INFO
    )

    if not logger.handlers:

        file_handler = logging.FileHandler(
            log_file,
            encoding="utf-8"
        )

        formatter = logging.Formatter(
            "%(asctime)s | "
            "%(levelname)s | "
            "%(message)s"
        )

        file_handler.setFormatter(
            formatter
        )

        logger.addHandler(
            file_handler
        )

    return logger