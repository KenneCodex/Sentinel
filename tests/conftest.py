"""Shared pytest configuration for the Sentinel test suite.

Test modules import from the top-level ``tools`` package. Without this file the
repository root only lands on ``sys.path`` when the suite happens to be invoked
from the root directory, or as a side effect of another test module inserting it
at import time. Anchoring the path here keeps every module independently
collectable, regardless of invocation directory or collection order.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
