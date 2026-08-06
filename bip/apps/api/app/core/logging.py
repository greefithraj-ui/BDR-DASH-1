import logging

from app.config.settings import Settings


def configure_logging(settings: Settings) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    logging.getLogger("bip").info("Starting %s in %s", settings.app_name, settings.environment)
