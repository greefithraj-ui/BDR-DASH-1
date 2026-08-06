"""Unit tests for bic.config (Sprint 1, Task T1.1)."""

import pytest

from bic.config import BicConfig, _assert_spec_constants, load_config


def test_package_importable():
    import bic

    assert bic.__doc__ is not None


def test_config_loads():
    cfg = load_config()
    assert isinstance(cfg, BicConfig)


def test_spec_constants():
    cfg = load_config()
    assert cfg.cadence == 30
    assert cfg.freshness_window == 60
    assert cfg.removal_confirmations == 3
    assert cfg.removal_grace == 120


def test_config_is_frozen():
    cfg = load_config()
    with pytest.raises(Exception):
        cfg.cadence = 15


def test_assertion_raises_on_drift():
    drifted = BicConfig(cadence=60)
    with pytest.raises(ValueError):
        _assert_spec_constants(drifted)
