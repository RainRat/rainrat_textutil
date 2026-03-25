import sys; import os; from pathlib import Path; sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))

import subprocess
import sys
from pathlib import Path

# Ensure repo root is on path

from sourcecombine import __version__

def test_version_flag():
    result = subprocess.run(
        [sys.executable, "sourcecombine.py", "--version"],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0
    assert f"sourcecombine.py {__version__}" in result.stdout.strip()
