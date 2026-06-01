import sys
import os
import io
import pytest
import copy
from pathlib import Path
from unittest.mock import MagicMock, patch
import sourcecombine
import utils

def test_export_config_error_handling(caplog):
    """Cover sourcecombine.py lines 4463-4465: error handling during config export."""
    from sourcecombine import main

    args = MagicMock()
    args.export_config = "invalid/path/config.yml"
    args.targets = ["."]
    # Minimum attributes to avoid AttributeError in main()
    args.config = None
    args.files_from = None
    args.init = False
    args.system_info = False
    args.list_placeholders = False
    args.list_languages = False
    args.verbose = False
    args.ai = False
    args.show_config = False
    args.restore = False
    args.delete_backups = False
    args.extract = False
    args.verify = False
    args.clean = False
    args.preview = False
    args.max_total_size = None
    args.max_tokens = None
    args.max_total_lines = None
    args.limit = None
    args.max_file_tokens = None
    args.max_file_lines = None
    args.min_tokens = None
    args.min_lines = None
    args.min_size = None
    args.max_size = None
    args.git_log = 0
    args.since = None
    args.until = None
    args.max_lines = None
    args.truncate_tokens = None
    args.skip_binary = False
    args.unique = False
    args.json_summary = None
    args.language = []
    args.header = None
    args.footer = None
    args.global_header = None
    args.global_footer = None
    args.max_size_placeholder = None
    args.repair = False
    args.list_placeholders = False
    args.export_config = "exported.yml"
    args.clipboard = False

    with patch("sourcecombine.argparse.ArgumentParser.parse_args", return_value=args), \
         patch("utils.save_yaml_config", side_effect=OSError("Disk Full")):
        with pytest.raises(SystemExit) as cm:
            main()
        assert cm.value.code == 1

    assert "Could not export configuration: Disk Full" in caplog.text

def test_extract_summary_json_template(tmp_path):
    """Cover sourcecombine.py line 4607: template rendering for summary_json in extract mode."""
    from sourcecombine import main

    # Use a real file that exists to avoid fallback logic issues
    combined_file = tmp_path / "combined.json"
    combined_file.write_text("[]")

    args = MagicMock()
    args.extract = True
    args.targets = [str(combined_file)]
    args.output = str(tmp_path)
    # Minimum attributes to avoid AttributeError in main()
    args.config = None
    args.files_from = None
    args.init = False
    args.system_info = False
    args.list_placeholders = False
    args.list_languages = False
    args.verbose = False
    args.ai = False
    args.show_config = False
    args.restore = False
    args.delete_backups = False
    args.verify = False
    args.clean = False
    args.preview = False
    args.max_total_size = None
    args.max_tokens = None
    args.max_total_lines = None
    args.limit = None
    args.max_file_tokens = None
    args.max_file_lines = None
    args.min_tokens = None
    args.min_lines = None
    args.min_size = None
    args.max_size = None
    args.git_log = 0
    args.since = None
    args.until = None
    args.max_lines = None
    args.truncate_tokens = None
    args.skip_binary = False
    args.unique = False
    args.json_summary = "summary_{{PROJECT_NAME}}.json" # Set via CLI
    args.language = []
    args.header = None
    args.footer = None
    args.global_header = None
    args.global_footer = None
    args.max_size_placeholder = None
    args.repair = False
    args.list_placeholders = False
    args.export_config = None
    args.dry_run = False
    args.list_files = False
    args.tree = False
    args.estimate_tokens = False
    args.keep_line_numbers = False
    args.clipboard = False
    args.no_clipboard = False
    args.format = None

    config = copy.deepcopy(utils.DEFAULT_CONFIG)
    config['project'] = {'name': 'TestProj'}

    mock_stats = {
        'project_name': 'TestProj',
        'total_included': 0,
        'top_files': [],
        'files_by_extension': {},
        'tokens_by_extension': {},
        'size_by_extension': {},
        'filter_reasons': {}
    }

    # Patch load_and_validate_config so it's not actually called with combined_file
    with patch("sourcecombine.argparse.ArgumentParser.parse_args", return_value=args), \
         patch("sourcecombine.load_and_validate_config", return_value=config), \
         patch("sourcecombine.read_file_best_effort", return_value=("[]", "utf-8")), \
         patch("sourcecombine.extract_files", return_value=mock_stats), \
         patch("sourcecombine._print_execution_summary"), \
         patch("sourcecombine._write_json_summary") as mock_write:

        with pytest.raises(SystemExit) as cm:
            main()
        assert cm.value.code == 0

        mock_write.assert_called_once()
        called_summary_path = mock_write.call_args[0][1]
        assert called_summary_path == "summary_TestProj.json"

def test_print_execution_summary_extra_metadata_and_deleted_status(capsys):
    """Cover sourcecombine.py lines 5594, 5596, 5869."""
    from sourcecombine import _print_execution_summary

    stats = {
        'project_name': 'MyProject',
        'project_version': '1.2.3',
        'project_license': 'MIT',
        'git_branch': 'main',
        'git_commit': 'abcdef',
        'total_discovered': 1,
        'total_included': 1,
        'total_size_bytes': 100,
        'token_count': 10,
        'total_lines': 5,
        'duration': 0.1,
        'top_files': [(10, 100, "deleted.txt", "D", 5)], # status "D"
        'files_by_extension': {".txt": 1},
        'tokens_by_extension': {".txt": 10},
        'size_by_extension': {".txt": 100},
        'total_tokens': 10,
        'filter_reasons': {}
    }

    args = MagicMock()
    args.limit = 0
    args.max_tokens = 0
    args.max_total_size = 0
    args.max_total_lines = 0

    with patch("sys.stderr", new=io.StringIO()) as mock_stderr:
        with patch("sys.stderr.isatty", return_value=True):
            _print_execution_summary(stats, args, pairing_enabled=False)
            output = mock_stderr.getvalue()

    assert "v1.2.3" in output
    assert "[MIT]" in output
    assert "\x1b[31m[D]\x1b[0m" in output
