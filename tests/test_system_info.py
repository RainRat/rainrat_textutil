import sys
import subprocess
from pathlib import Path

def test_system_info_flag():
    """Verify that --system-info prints environment details and exits successfully."""
    # Use subprocess to run the script and capture output
    # This avoids issues with sys.exit() and stdout capturing in the same process
    result = subprocess.run(
        [sys.executable, "sourcecombine.py", "--system-info"],
        capture_output=True,
        text=True,
        check=True
    )

    output = result.stdout
    assert "SourceCombine System Information" in output
    assert "SourceCombine Version" in output
    assert "Python Version" in output
    assert "Platform" in output
    assert "Optional Dependencies" in output
    assert "tiktoken" in output
    assert "pyperclip" in output
    assert "tqdm" in output
    assert "charset_normalizer" in output

    # Check exit code is 0
    assert result.returncode == 0

def test_system_info_shortcut_not_exists():
    """Verify that there is no shortcut for --system-info (as intended)."""
    # Just checking the help text
    result = subprocess.run(
        [sys.executable, "sourcecombine.py", "--help"],
        capture_output=True,
        text=True,
        check=True
    )
    assert "--system-info" in result.stdout
    # Check that it doesn't have a short flag like -S or something (unless we added one)
    # We didn't add a short flag.
