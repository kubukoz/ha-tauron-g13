"""Load zones.py as a standalone module so the pure-engine tests don't require
Home Assistant to be installed (the package __init__ imports homeassistant)."""

import importlib.util
import sys
from pathlib import Path

_ZONES = Path(__file__).resolve().parent.parent / "zones.py"
_spec = importlib.util.spec_from_file_location("zones", _ZONES)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
# Expose as a bare top-level module the tests import.
sys.modules["zones"] = _mod
