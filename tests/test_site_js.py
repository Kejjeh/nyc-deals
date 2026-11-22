"""Runs the site's JavaScript tests (tests/js/*.test.mjs) under the node on PATH."""
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not on PATH")
def test_site_javascript():
    run = subprocess.run(["node", "--test", "tests/js/*.test.mjs"], cwd=ROOT, capture_output=True, text=True)
    assert run.returncode == 0, run.stdout + run.stderr
