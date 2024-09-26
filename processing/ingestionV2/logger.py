import logging


def setup_logger():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        filename="rhel_upgrade_reporting.log",
    )
    return logging.getLogger(__name__)


def get_logger(name):
    return logging.getLogger(name)
