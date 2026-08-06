#!/usr/bin/env python3
"""
Launcher for the machine manager. The real implementation lives at
D:\\BDR\\manage_machines.py; this file exists so shortcuts that point into
the MACHINES folder keep working. Run it from anywhere.
"""
import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_TARGET = _ROOT / "manage_machines.py"

if not _TARGET.exists():
    print(f"Machine manager not found: {_TARGET}")
    input("\nPress Enter to exit...")
    sys.exit(1)

sys.path.insert(0, str(_ROOT))
exec(compile(_TARGET.read_text(encoding="utf-8"), str(_TARGET), "exec"))
