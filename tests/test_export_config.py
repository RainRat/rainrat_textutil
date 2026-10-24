import pytest
import os
from pathlib import Path
from unittest.mock import MagicMock, patch
import sourcecombine
import utils
import copy

def test_export_config_flag_logic(tmp_path, monkeypatch):
    """Test the --export-config logic in main()."""
    monkeypatch.chdir(tmp_path)

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

def test_export_cfg_shortcut_alias_logic(tmp_path, monkeypatch):
    """Test that --export-cfg shortcut alias behaves identically to --export-config."""
    monkeypatch.chdir(tmp_path)

    args = MagicMock()
    args.targets = ["."]
    args.output = None
    args.config = None
    args.export_config = "exported_shortcut.yml"
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
        assert mock_save.call_args[0][0] == "exported_shortcut.yml"

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


def test_export_cfg_shortcut_alias_cli(tmp_path, monkeypatch):
    """Test --export-cfg from CLI argv without mocking parse_args."""
    monkeypatch.chdir(tmp_path)
    with patch("sys.argv", ["sourcecombine.py", "--export-cfg", str(tmp_path / "exported_cfg.yml")]):
        with pytest.raises(SystemExit) as excinfo:
            sourcecombine.main()
        assert excinfo.value.code == 0
    assert (tmp_path / "exported_cfg.yml").exists()


def test_export_config_helper_default_config(tmp_path):
    """Test export_config helper function with default config fallback."""
    out_file = tmp_path / "default_export.yml"
    sourcecombine.export_config(out_file)
    assert out_file.exists()
    content = out_file.read_text(encoding="utf-8")
    assert "search:" in content


def test_export_config_helper_json_file(tmp_path):
    """Test export_config helper function saving JSON format based on file extension."""
    out_file = tmp_path / "custom.json"
    custom_cfg = copy.deepcopy(utils.DEFAULT_CONFIG)
    custom_cfg["logging"]["level"] = "DEBUG"

    sourcecombine.export_config(out_file, config=custom_cfg)
    assert out_file.exists()
    import json
    data = json.loads(out_file.read_text(encoding="utf-8"))
    assert data["logging"]["level"] == "DEBUG"


def test_export_config_helper_json_format_flag(tmp_path):
    """Test export_config helper function with explicit json_format=True."""
    out_file = tmp_path / "custom.config"
    custom_cfg = copy.deepcopy(utils.DEFAULT_CONFIG)
    custom_cfg["search"]["max_depth"] = 42

    sourcecombine.export_config(out_file, config=custom_cfg, json_format=True)
    assert out_file.exists()
    import json
    data = json.loads(out_file.read_text(encoding="utf-8"))
    assert data["search"]["max_depth"] == 42


def test_export_config_helper_stdout_yaml(capsys):
    """Test export_config helper function streaming YAML to stdout (-)."""
    custom_cfg = copy.deepcopy(utils.DEFAULT_CONFIG)
    custom_cfg["logging"]["level"] = "WARNING"

    sourcecombine.export_config("-", config=custom_cfg)
    captured = capsys.readouterr().out
    assert "level: WARNING" in captured


def test_export_config_helper_stdout_json(capsys):
    """Test export_config helper function streaming JSON to stdout (-) with json_format=True."""
    import json
    custom_cfg = copy.deepcopy(utils.DEFAULT_CONFIG)
    custom_cfg["search"]["max_depth"] = 7

    sourcecombine.export_config("-", config=custom_cfg, json_format=True)
    captured = capsys.readouterr().out
    data = json.loads(captured)
    assert data["search"]["max_depth"] == 7


def test_export_config_helper_directory_target(tmp_path):
    """Test export_config helper function targeting a directory."""
    target_dir = tmp_path / "subfolder"
    target_dir.mkdir()
    custom_cfg = copy.deepcopy(utils.DEFAULT_CONFIG)

    sourcecombine.export_config(target_dir, config=custom_cfg, json_format=True)
    exported_file = target_dir / "sourcecombine.json"
    assert exported_file.exists()


def test_export_config_helper_os_error_handling(tmp_path, caplog):
    """Test export_config helper function handling OSError exceptions."""
    import logging
    invalid_path = tmp_path / "nonexistent_dir" / "nested" / "file.json"

    with patch("builtins.open", side_effect=OSError("Permission denied")):
        with caplog.at_level(logging.ERROR):
            with pytest.raises(SystemExit) as excinfo:
                sourcecombine.export_config(invalid_path)
            assert excinfo.value.code == 1
    assert "Could not export configuration" in caplog.text
