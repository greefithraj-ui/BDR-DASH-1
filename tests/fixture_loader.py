"""Loader for the BIC golden fixture corpus.

Each fixture is a directory under tests/fixtures/ containing rings.json and
optionally bdr.json, mirroring the live per-machine payload structure.
"""

import json
from dataclasses import dataclass
from pathlib import Path

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


@dataclass(frozen=True)
class MachineFixture:
    """One machine snapshot: the rings payload and the bdr payload."""

    name: str
    rings: dict
    bdr: dict | None


def load_fixture(name: str) -> MachineFixture:
    """Load a named fixture; bdr is None when the fixture has no bdr file."""
    fixture_dir = FIXTURES_DIR / name
    rings = _read_json(fixture_dir / "rings.json")
    bdr_path = fixture_dir / "bdr.json"
    bdr = _read_json(bdr_path) if bdr_path.exists() else None
    return MachineFixture(name=name, rings=rings, bdr=bdr)


def list_fixtures() -> tuple[str, ...]:
    """Return sorted fixture names (directories under tests/fixtures/)."""
    return tuple(
        sorted(p.name for p in FIXTURES_DIR.iterdir() if p.is_dir())
    )


def _read_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)
