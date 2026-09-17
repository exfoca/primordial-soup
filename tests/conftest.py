# SPDX-License-Identifier: MIT
# Copyright (c) 2026 exfoca

"""Isolamento da fonte declarativa de configuracao durante a suite."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import tempfile


_CONFIG_ENV = "PRIMORDIAL_SOUP_CONFIG"
_REPO_ROOT = Path(__file__).resolve().parents[1]
_PACKAGED_BASELINE = _REPO_ROOT / "primordial_soup" / ".env"
_SESSION_DIR = Path(tempfile.mkdtemp(prefix="primordial-soup-tests-"))
_SESSION_CONFIG = _SESSION_DIR / ".env"
_PREVIOUS_OVERRIDE = os.environ.get(_CONFIG_ENV)

shutil.copyfile(_PACKAGED_BASELINE, _SESSION_CONFIG)
os.environ[_CONFIG_ENV] = str(_SESSION_CONFIG)


def pytest_sessionfinish(session, exitstatus):
    """Remove a copia temporaria e restaura o environment do chamador."""
    del session, exitstatus
    if _PREVIOUS_OVERRIDE is None:
        os.environ.pop(_CONFIG_ENV, None)
    else:
        os.environ[_CONFIG_ENV] = _PREVIOUS_OVERRIDE
    shutil.rmtree(_SESSION_DIR, ignore_errors=True)
