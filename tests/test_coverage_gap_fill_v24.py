import pytest
import sys
import os
import json
import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

# Ensure consistent imports that point to the root directory
sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))
import sourcecombine
import utils

def test_export_config_os_error_handling(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    args = MagicMock()
    args.targets = ["."]
    args.export_config = "failed_export.yml"
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
    args.max_file_tokens = 0
    args.max_file_lines = 0
    args.min_tokens = 0
    args.min_lines = 0
    args.max_depth = None
    args.git_files = False
    args.unique = False
    args.skip_binary = False
    args.sort = None
    args.reverse = False
    args.limit = 0
    args.max_tokens = 0
    args.max_total_size = 0
    args.max_total_lines = 0
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
    args.keep_line_numbers = False
    args.config = None
    args.output = None
    args.truncate_tokens = 0
    args.max_lines = 0

    with patch("sourcecombine.argparse.ArgumentParser.parse_args", return_value=args), \
         patch("sourcecombine.utils.load_yaml_config", return_value=utils.DEFAULT_CONFIG.copy()), \
         patch("sourcecombine.utils.save_yaml_config", side_effect=OSError("Disk full")), \
         patch("logging.error") as mock_log_error:

        with pytest.raises(SystemExit) as excinfo:
            sourcecombine.main()

        assert excinfo.value.code == 1
        mock_log_error.assert_called_once()
        assert "Disk full" in str(mock_log_error.call_args[0][1])

def test_extract_summary_json_placeholder_rendering(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    combined_file = tmp_path / "combined_files.txt"
    combined_file.write_text("---\nfile.txt\n---\ncontent\n--- end file.txt ---")

    args = MagicMock()
    args.extract = str(combined_file)
    args.targets = [str(combined_file)]
    args.output = None
    args.config = None
    args.show_config = False
    args.export_config = None
    args.init = False
    args.system_info = False
    args.list_placeholders = False
    args.list_languages = False
    args.verbose = False
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
    args.max_file_tokens = 0
    args.max_file_lines = 0
    args.min_tokens = 0
    args.min_lines = 0
    args.max_depth = None
    args.git_files = False
    args.unique = False
    args.skip_binary = False
    args.sort = None
    args.reverse = False
    args.limit = 0
    args.max_tokens = 0
    args.max_total_size = 0
    args.max_total_lines = 0
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
    args.keep_line_numbers = False
    args.dry_run = False
    args.truncate_tokens = 0
    args.max_lines = 0

    config = utils.DEFAULT_CONFIG.copy()
    config['output']['summary_json'] = "summary_{{PROJECT_NAME}}.json"
    config['processing'] = {}

    with patch("sourcecombine.argparse.ArgumentParser.parse_args", return_value=args), \
         patch("sourcecombine.utils.load_yaml_config", return_value=config), \
         patch("sourcecombine._write_json_summary") as mock_write_json:

        with pytest.raises(SystemExit) as excinfo:
            sourcecombine.main()

        assert excinfo.value.code == 0
        mock_write_json.assert_called_once()
        summary_path = mock_write_json.call_args[0][1]
        assert "summary_" in summary_path
        assert "{{" not in summary_path

def test_print_execution_summary_metadata_and_deleted_status(capsys):
    stats = {
        'project_name': 'TestProj',
        'project_version': '1.0.0',
        'project_license': 'MIT',
        'git_branch': 'main',
        'git_commit_short': 'abcdef',
        'total_files': 1,
        'total_size_bytes': 100,
        'total_lines': 10,
        'total_tokens': 50,
        'top_files': [(50, 100, 'deleted_file.txt', 'D', 10)],
        'files_by_extension': {'.txt': 1},
        'size_by_extension': {'.txt': 100},
        'lines_by_extension': {'.txt': 10},
        'tokens_by_extension': {'.txt': 50},
        'folders': {}
    }
    args = MagicMock()
    args.compact = False
    args.dry_run = False
    args.estimate_tokens = False
    args.list_files = False
    args.tree = False
    args.extract = False
    args.apply_in_place = False

    sourcecombine._print_execution_summary(stats, args, pairing_enabled=False, destination_desc="dest", duration=1.0, source_desc="source")

    captured = capsys.readouterr().err # _print_execution_summary prints to stderr
    assert "TestProj v1.0.0 [MIT]" in captured
    assert "[D]" in captured
