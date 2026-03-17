import subprocess
import yaml

def test_show_config_defaults():
    """Test that --show-config displays default values."""
    result = subprocess.run(
        ["python", "sourcecombine.py", "--show-config"],
        capture_output=True,
        text=True,
        check=True
    )
    # The first line might be "INFO: Final merged configuration:" if logging is on
    # but since it's on stderr and we captured stdout, we should just get YAML
    config = yaml.safe_load(result.stdout)
    assert config["output"]["format"] == "text"
    assert config["search"]["root_folders"] == ["."]

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
