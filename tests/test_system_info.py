import sys; import os; from pathlib import Path; sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))

import sys
import subprocess
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
    assert "=== SYSTEM INFORMATION ===" in output
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

def test_sys_info_shortcut_alias():
    """Verify that --sys-info shortcut alias prints environment details identically."""
    result = subprocess.run(
        [sys.executable, "sourcecombine.py", "--sys-info"],
        capture_output=True,
        text=True,
        check=True
    )

    output = result.stdout
    assert "=== SYSTEM INFORMATION ===" in output
    assert "SourceCombine Version" in output
    assert "Python Version" in output
    assert result.returncode == 0


def test_system_info_help_text():
    """Verify that --system-info and --sys-info shortcut alias are present in help text."""
    result = subprocess.run(
        [sys.executable, "sourcecombine.py", "--help"],
        capture_output=True,
        text=True,
        check=True
    )
    assert "--system-info" in result.stdout
    assert "--sys-info" in result.stdout

def test_print_system_info_with_and_without_optional_dependencies(capsys):
    from sourcecombine import print_system_info
    with patch("importlib.util.find_spec", side_effect=lambda name: MagicMock() if name == "tiktoken" else None):
        print_system_info()

    captured = capsys.readouterr()
    assert "=== SYSTEM INFORMATION ===" in captured.out
    assert "tiktoken" in captured.out
    assert "Installed" in captured.out
    assert "pyperclip" in captured.out
    assert "Not found" in captured.out

def test_print_system_info_handles_find_spec_exception(capsys):
    import json
    from sourcecombine import print_system_info
    with patch("importlib.util.find_spec", side_effect=RuntimeError("Resolution error")):
        print_system_info(json_format=False)
        captured = capsys.readouterr()
        assert "=== SYSTEM INFORMATION ===" in captured.out
        assert "Not found" in captured.out

        print_system_info(json_format=True)
        captured_json = capsys.readouterr()
        data = json.loads(captured_json.out)
        assert data["dependencies"]["tiktoken"]["installed"] is False

def test_print_system_info_config_autodiscovery(tmp_path, monkeypatch, capsys):
    import json
    from sourcecombine import print_system_info

    monkeypatch.chdir(tmp_path)

    # 1. When no config file exists
    print_system_info(json_format=False)
    out1 = capsys.readouterr().out
    assert "Local Config:" in out1
    assert "Not found (N/A)" in out1

    print_system_info(json_format=True)
    out_json1 = capsys.readouterr().out
    data1 = json.loads(out_json1)
    assert data1["local_config"]["found"] is False
    assert data1["local_config"]["path"] is None

    # 2. When sourcecombine.yaml exists
    yaml_config = tmp_path / "sourcecombine.yaml"
    yaml_config.write_text("output:\n  format: text\n")

    print_system_info(json_format=False)
    out2 = capsys.readouterr().out
    assert "Local Config:" in out2
    assert "Found" in out2
    assert "sourcecombine.yaml" in out2

    print_system_info(json_format=True)
    out_json2 = capsys.readouterr().out
    data2 = json.loads(out_json2)
    assert data2["local_config"]["found"] is True
    assert "sourcecombine.yaml" in data2["local_config"]["path"]
