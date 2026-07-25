import pytest
import utils
from sourcecombine import find_and_combine_files

@pytest.fixture
def base_config(tmp_path):
    return {
        'search': {'root_folders': [str(tmp_path)]},
        'output': {'mirror': True},
        'pairing': {'enabled': False},
        'filters': {},
        'processing': {},
    }

def test_mirror_mode_clipboard_conflict(tmp_path, base_config):
    with pytest.raises(utils.InvalidConfigError, match="Mirror mode and clipboard cannot be used at the same time."):
        find_and_combine_files(base_config, str(tmp_path / "out"), clipboard=True)

def test_mirror_mode_terminal_conflict(base_config):
    with pytest.raises(utils.InvalidConfigError, match="Mirror mode cannot output to the terminal."):
        find_and_combine_files(base_config, "-")

def test_mirror_mode_unsupported_format_json(tmp_path, base_config):
    with pytest.raises(utils.InvalidConfigError, match="Mirror mode does not support JSON format."):
        find_and_combine_files(base_config, str(tmp_path / "out"), output_format='json')

def test_mirror_mode_unsupported_format_csv(tmp_path, base_config):
    with pytest.raises(utils.InvalidConfigError, match="Mirror mode does not support CSV format."):
        find_and_combine_files(base_config, str(tmp_path / "out"), output_format='csv')

def test_mirror_mode_unsupported_format_jsonl(tmp_path, base_config):
    with pytest.raises(utils.InvalidConfigError, match="Mirror mode does not support JSONL format."):
        find_and_combine_files(base_config, str(tmp_path / "out"), output_format='jsonl')

def test_mirror_mode_unsupported_format_manifest(tmp_path, base_config):
    with pytest.raises(utils.InvalidConfigError, match="Mirror mode does not support MANIFEST format."):
        find_and_combine_files(base_config, str(tmp_path / "out"), output_format='manifest')


def test_mirror_mode_cli_no_output(tmp_path):
    import sys
    import yaml
    from unittest.mock import patch
    from sourcecombine import main

    config_file = tmp_path / "config.yml"
    config_data = {
        "output": {
            "mirror": True,
            "file": "",
            "folder": ""
        }
    }
    with open(config_file, "w") as f:
        yaml.safe_dump(config_data, f)

    test_args = ["sourcecombine.py", str(config_file), str(tmp_path)]
    with patch.object(sys, 'argv', test_args):
        with pytest.raises(utils.InvalidConfigError, match="You must set an output folder for mirror mode."):
            main()
