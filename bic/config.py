"""BIC runtime configuration, fixed to Architecture Specification v1.0.

Constants are NOT environment-driven and NOT overridable: they are the frozen
spec values and must not drift.
"""

from dataclasses import dataclass

CADENCE_SECONDS = 30
FRESHNESS_WINDOW_SECONDS = 60
REMOVAL_CONFIRMATIONS = 3
REMOVAL_GRACE_SECONDS = 120

_EXPECTED_SPEC = {
    "cadence": CADENCE_SECONDS,
    "freshness_window": FRESHNESS_WINDOW_SECONDS,
    "removal_confirmations": REMOVAL_CONFIRMATIONS,
    "removal_grace": REMOVAL_GRACE_SECONDS,
}


@dataclass(frozen=True)
class BicConfig:
    """Runtime configuration for the BIC collector."""

    cadence: int = CADENCE_SECONDS
    freshness_window: int = FRESHNESS_WINDOW_SECONDS
    removal_confirmations: int = REMOVAL_CONFIRMATIONS
    removal_grace: int = REMOVAL_GRACE_SECONDS


def load_config() -> BicConfig:
    """Build the BIC configuration and verify it matches the frozen spec."""
    cfg = BicConfig()
    _assert_spec_constants(cfg)
    return cfg


def _assert_spec_constants(cfg: BicConfig) -> None:
    """Raise ValueError if any config value drifted from the frozen spec."""
    for name, expected in _EXPECTED_SPEC.items():
        actual = getattr(cfg, name)
        if actual != expected:
            raise ValueError(
                f"config drift: {name} is {actual}, Architecture Specification "
                f"v1.0 requires {expected}"
            )
