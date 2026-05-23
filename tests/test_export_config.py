import pytest
import os
from pathlib import Path
from unittest.mock import MagicMock, patch
import sourcecombine
import utils
import copy

def test_export_config_flag_logic(tmp_path):
    """Test the --export-config logic in main()."""
    os.chdir(tmp_path)

    # Mocking arguments for main()
    args = MagicMock()
    args.targets = ["."]
    args.output = None
    args.config = None
    args.export_config = "exported.yml"
    args.show_config = False
    args.init = False
    args.system_info = False
    args.list_placeholders = False
    args.list_languages = False
    args.verbose = False
    args.extract = False
    args.restore = False
    args.delete_backups = False
    args.ai = False
    args.map_lang = []
    args.language = []
    args.include = []
    args.files_from = None
    args.exclude_file = []
    args.exclude_folder = []
    args.exclude_language = []
    args.since = None
    args.until = None
    args.min_size = None
    args.max_size = None
    args.git_diff = False
    args.staged = False
    args.unstaged = False
    args.grep = None
    args.exclude_grep = None
    args.max_file_tokens = None
    args.max_file_lines = None
    args.min_tokens = None
    args.min_lines = None
    args.max_depth = None
    args.git_files = False
    args.unique = False
    args.skip_binary = False
    args.sort = None
    args.reverse = False
    args.limit = None
    args.max_tokens = None
    args.max_total_size = None
    args.max_total_lines = None
    args.format = None
    args.line_numbers = False
    args.toc = False
    args.include_tree = False
    args.overview = False
    args.git_log = 0
    args.include_diff = False
    args.header = None
    args.footer = None
    args.global_header = None
    args.global_footer = None
    args.max_size_placeholder = None
    args.json_summary = None
    args.pair = None
    args.include_unpaired = False
    args.pair_template = None
    args.estimate_tokens = False
    args.list_files = False
    args.tree = False
    args.diff = False
    args.compact = False
    args.apply_in_place = False
    args.create_backups = True
    args.verify = False
    args.clean = False
    args.preview = False
    args.clipboard = False
    args.no_clipboard = False

    config = copy.deepcopy(utils.DEFAULT_CONFIG)

    with patch("sourcecombine.argparse.ArgumentParser.parse_args", return_value=args), \
         patch("sourcecombine.utils.load_yaml_config", return_value=config), \
         patch("sourcecombine.utils.save_yaml_config") as mock_save:

        with pytest.raises(SystemExit) as excinfo:
            sourcecombine.main()

        assert excinfo.value.code == 0
        mock_save.assert_called_once()
        assert mock_save.call_args[0][0] == "exported.yml"

def test_save_yaml_config_utils(tmp_path):
    """Test utils.save_yaml_config directly."""
    config_file = tmp_path / "test.yml"
    config_data = {"key": "value", "nested": {"a": 1}}

    utils.save_yaml_config(str(config_file), config_data)

    assert config_file.exists()
    content = config_file.read_text()
    assert "# SourceCombine Configuration" in content
    assert "key: value" in content
    assert "nested:" in content
    assert "a: 1" in content

def test_save_yaml_config_no_yaml(tmp_path, monkeypatch):
    """Test utils.save_yaml_config when yaml is missing."""
    monkeypatch.setattr(utils, "yaml", None)
    with pytest.raises(utils.InvalidConfigError, match="PyYAML' library is required"):
        utils.save_yaml_config("any.yml", {})
