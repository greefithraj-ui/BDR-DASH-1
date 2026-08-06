"""Unit tests for bic.main poll-loop framework (Sprint 1, Task T1.2)."""

import threading
import time

from bic.config import BicConfig
from bic.main import _sleep_until_next, main, run_poll_cycle


def test_sleep_zero_cadence_returns_true():
    assert _sleep_until_next(time.monotonic(), 0) is True


def test_tick_interval_honored():
    started = time.monotonic()
    assert _sleep_until_next(started, 1) is True
    assert 1.0 <= time.monotonic() - started < 3.0


def test_sleep_aborts_on_shutdown():
    shutdown = threading.Event()
    threading.Timer(0.2, shutdown.set).start()
    started = time.monotonic()
    assert _sleep_until_next(started, 60, shutdown) is False
    assert time.monotonic() - started < 1.0


def test_sleep_returns_false_when_shutdown_already_set():
    shutdown = threading.Event()
    shutdown.set()
    assert _sleep_until_next(time.monotonic(), 60, shutdown) is False


def test_run_poll_cycle_with_zero_cadence():
    run_poll_cycle(BicConfig(cadence=0), threading.Event())


def test_run_poll_cycle_returns_when_shutdown_set():
    shutdown = threading.Event()
    shutdown.set()
    run_poll_cycle(BicConfig(), shutdown)


def test_main_exits_on_shutdown():
    shutdown = threading.Event()
    thread = threading.Thread(
        target=main, kwargs={"shutdown": shutdown}, daemon=True
    )
    thread.start()
    time.sleep(0.5)
    shutdown.set()
    thread.join(timeout=5)
    assert not thread.is_alive()
