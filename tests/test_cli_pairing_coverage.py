import sys
import yaml
import pytest
from unittest.mock import patch
import sourcecombine

def test_main_pairing_cli_injection(capsys):
    """Test that pairing CLI flags are correctly injected into the configuration."""
    base_config = {
        'search': {'root_folders': ['.']},
        'logging': {'level': 'INFO'},
        'pairing': None,
        'output': None
    }

    with patch("sourcecombine.load_and_validate_config", return_value=base_config):
        with patch("sys.argv", [
            "sourcecombine.py",
            "--config", "dummy.yml",
            "--pair", "cpp", "h",
            "--pair", ".ts", ".tsx",
            "--include-unpaired",
            "--pair-template", "{{STEM}}.combined",
            "--show-config"
        ]):
            with pytest.raises(SystemExit) as excinfo:
                sourcecombine.main()
            assert excinfo.value.code == 0

    captured = capsys.readouterr()
    config = yaml.safe_load(captured.out)

    assert config["pairing"]["enabled"] is True
    assert ".cpp" in config["pairing"]["source_extensions"]
    assert ".h" in config["pairing"]["header_extensions"]
    assert ".ts" in config["pairing"]["source_extensions"]
    assert ".tsx" in config["pairing"]["header_extensions"]
    assert config["pairing"]["include_mismatched"] is True
    assert config["output"]["paired_filename_template"] == "{{STEM}}.combined"

def test_main_pairing_cli_injection_existing_config(capsys):
    """Test that pairing CLI flags append to existing configuration."""
    base_config = {
        'search': {'root_folders': ['.']},
        'logging': {'level': 'INFO'},
        'pairing': {
            'enabled': False,
            'source_extensions': ['.py'],
            'header_extensions': ['.pyi']
        },
        'output': {
            'paired_filename_template': 'old.template'
        }
    }

    with patch("sourcecombine.load_and_validate_config", return_value=base_config):
        with patch("sys.argv", [
            "sourcecombine.py",
            "--config", "dummy.yml",
            "--pair", "cpp", "h",
            "--show-config"
        ]):
            with pytest.raises(SystemExit) as excinfo:
                sourcecombine.main()
            assert excinfo.value.code == 0

    captured = capsys.readouterr()
    config = yaml.safe_load(captured.out)

    assert config["pairing"]["enabled"] is True
    assert ".py" in config["pairing"]["source_extensions"]
    assert ".cpp" in config["pairing"]["source_extensions"]
    assert ".pyi" in config["pairing"]["header_extensions"]
    assert ".h" in config["pairing"]["header_extensions"]

def test_main_pairing_cli_injection_uninitialized_lists(capsys):
    """Test that pairing CLI flags work even if source/header extensions are None (hitting lines 3116, 3119)."""
    bad_config = {
        'search': {'root_folders': ['.']},
        'logging': {'level': 'INFO'},
        'pairing': {
            'source_extensions': None,
            'header_extensions': None
        },
        'output': {}
    }

    # By mocking sourcecombine.utils.validate_config AND sourcecombine.validate_config,
    # we prevent it from filling the default [] for None
    with patch("sourcecombine.load_and_validate_config", return_value=bad_config):
        with patch("sourcecombine.utils.validate_config"), patch("sourcecombine.validate_config"):
            with patch("sys.argv", [
                "sourcecombine.py",
                "--config", "dummy.yml",
                "--pair", "cpp", "h",
                "--show-config"
            ]):
                with pytest.raises(SystemExit) as excinfo:
                    sourcecombine.main()
                assert excinfo.value.code == 0

    captured = capsys.readouterr()
    config = yaml.safe_load(captured.out)

    assert config["pairing"]["enabled"] is True
    assert ".cpp" in config["pairing"]["source_extensions"]
    assert ".h" in config["pairing"]["header_extensions"]
