from pathlib import Path
import pytest
from unittest.mock import patch
import yaml
import copy

import sourcecombine
import utils

def test_path_resolve_oserror_coverage(tmp_path):
    file1 = tmp_path / "file1.txt"
    file1.write_text("content1")

    config = copy.deepcopy(sourcecombine.DEFAULT_CONFIG)
    for section in ['search', 'filters', 'output', 'processing', 'pairing', 'logging']:
        if section not in config or config[section] is None:
            config[section] = {}

    config['search'].update({
        'root_folders': [str(tmp_path)],
        'recursive': True
    })
    config['filters'].update({
        'unique': True,
        'exclusions': {'filenames': [], 'folders': []}
    })
    config['output'].update({
        'sort_by': 'name'
    })

    resolve_calls = []
    original_resolve = Path.resolve
    def side_effect(path_instance, *args, **kwargs):
        resolve_calls.append(path_instance)
        if len(resolve_calls) == 2:
            raise OSError("Mocked resolution error")
        return original_resolve(path_instance)

    with patch.object(Path, "resolve", autospec=True, side_effect=side_effect):
        stats = sourcecombine.find_and_combine_files(config, output_path=str(tmp_path / "out.txt"))

    assert stats['total_files'] == 1
    assert (tmp_path / "out.txt").exists()

def test_main_unique_flag_injection(capsys):
    with patch("sys.argv", ["sourcecombine.py", "--unique", "--show-config"]):
        with pytest.raises(SystemExit) as excinfo:
            sourcecombine.main()
        assert excinfo.value.code == 0

    captured = capsys.readouterr()
    config = yaml.safe_load(captured.out)
    assert config["filters"]["unique"] is True

def test_validate_config_unique_non_bool():
    config = {
        "filters": {"unique": "not-a-bool"},
        "search": {"root_folders": ["."]}
    }
    with pytest.raises(utils.InvalidConfigError, match="filters.unique must be true or false"):
        utils.validate_config(config)
