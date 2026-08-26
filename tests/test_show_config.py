import sys; import os; from pathlib import Path; sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))

import subprocess
import yaml

def test_show_config_defaults():
    """Test that --show-config displays default values and no stderr log clutter."""
    result = subprocess.run(
        ["python", "sourcecombine.py", "--show-config"],
        capture_output=True,
        text=True,
        check=True
    )
    config = yaml.safe_load(result.stdout)
    assert config["output"]["format"] == "text"
    assert config["search"]["root_folders"] == ["."]
    assert "Final merged configuration:" not in result.stderr
    assert "No config file found" not in result.stderr

def test_stdout_streaming_config_commands_clean_stderr():
    """Test that stdout streaming configuration commands output clean text without INFO log clutter on stderr."""
    for flag in ["--show-config", "--export-config", "--init", "--init-ignore"]:
        cmd = ["python", "sourcecombine.py", flag, "-"] if flag != "--show-config" else ["python", "sourcecombine.py", flag]
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        assert res.stdout.strip() != ""
        assert "Saving configuration to standard output" not in res.stderr
        assert "Final merged configuration:" not in res.stderr

def test_show_config_overrides():
    """Test that --show-config reflects CLI overrides."""
    result = subprocess.run(
        ["python", "sourcecombine.py", "src", "-o", "out.md", "--ai", "--show-config"],
        capture_output=True,
        text=True,
        check=True
    )
    config = yaml.safe_load(result.stdout)
    assert config["search"]["root_folders"] == ["src"]
    assert config["output"]["file"] == "out.md"
    assert config["output"]["format"] == "markdown"
    assert config["output"]["add_line_numbers"] is True
    assert config["output"]["table_of_contents"] is True
    assert config["output"]["include_tree"] is True

def test_show_config_with_file_override():
    """Test that --show-config handles explicit file output and format detection."""
    result = subprocess.run(
        ["python", "sourcecombine.py", "-o", "test.json", "--show-config"],
        capture_output=True,
        text=True,
        check=True
    )
    config = yaml.safe_load(result.stdout)
    assert config["output"]["file"] == "test.json"
    assert config["output"]["format"] == "json"
