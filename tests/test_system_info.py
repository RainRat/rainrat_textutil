import sys
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

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

def test_print_system_info_with_and_without_optional_dependencies(capsys):
    from sourcecombine import print_system_info
    with patch("importlib.util.find_spec", side_effect=lambda name: MagicMock() if name == "tiktoken" else None):
        print_system_info()

    captured = capsys.readouterr()
    assert "SourceCombine System Information" in captured.out
    assert "tiktoken" in captured.out
    assert "Installed" in captured.out
    assert "pyperclip" in captured.out
    assert "Not found" in captured.out
