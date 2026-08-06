"""BIC entrypoint: the 30-second poll-loop framework.

Ticks every BicConfig.cadence seconds, exits cleanly on SIGINT/SIGTERM or an
injected shutdown event, and performs no data work yet.
"""

import logging
import signal
import threading
import time

from bic.config import BicConfig, load_config

logger = logging.getLogger(__name__)


def main(shutdown: threading.Event | None = None) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    cfg = load_config()
    if shutdown is None:
        shutdown = threading.Event()
    if threading.current_thread() is threading.main_thread():
        signal.signal(signal.SIGINT, _make_signal_handler(shutdown))
        signal.signal(signal.SIGTERM, _make_signal_handler(shutdown))
    logger.info("bic starting (cadence=%ss)", cfg.cadence)
    try:
        while not shutdown.is_set():
            run_poll_cycle(cfg, shutdown)
    finally:
        logger.info("bic stopping")


def run_poll_cycle(cfg: BicConfig, shutdown: threading.Event) -> None:
    started = time.monotonic()
    if shutdown.is_set():
        return
    logger.info("poll cycle work executed (%.3fs)", time.monotonic() - started)
    _sleep_until_next(started, cfg.cadence, shutdown)


def _sleep_until_next(
    now: float,
    cadence: int,
    shutdown: threading.Event | None = None,
) -> bool:
    deadline = now + cadence
    while True:
        if shutdown is not None and shutdown.is_set():
            return False
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return True
        if shutdown is not None:
            shutdown.wait(timeout=min(remaining, 0.2))
        else:
            time.sleep(min(remaining, 0.2))


def _make_signal_handler(shutdown: threading.Event):
    def _handler(signum: int, frame) -> None:
        logger.info("signal %s received", signum)
        shutdown.set()

    return _handler


if __name__ == "__main__":
    main()
