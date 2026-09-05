#!/usr/bin/env python3
"""doc-health.py の配布時テスト。"""

import importlib.util
import sys
from pathlib import Path

SCRIPT = Path(__file__).with_name("doc-health.py")
SPEC = importlib.util.spec_from_file_location("doc_health", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)

raise SystemExit(MODULE.selftest())
