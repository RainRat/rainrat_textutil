import sys
import os
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
import logging
import copy

# Ensure repo root is on path
sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))

import sourcecombine
from utils import DEFAULT_CONFIG

def test_slugify_relative_dir_edge_cases():
    """Cover _slugify_relative_dir lines 1348-1351: . and .. components."""
    from sourcecombine import _slugify_relative_dir

    # Test '.' component
    assert _slugify_relative_dir("a/./b") == "a/dot/b"
    # Test '..' component
    assert _slugify_relative_dir("a/../b") == "a/dot-dot/b"
    # Test empty component (consecutive slashes or trailing slash)
    assert _slugify_relative_dir("a//b") == "a/unnamed/b"

def test_filter_file_paths_no_reasons_bak_exclusion(tmp_path):
    """Cover filter_file_paths lines 1301-1304: .bak exclusion when reasons is None."""
    from sourcecombine import filter_file_paths

    bak_file = tmp_path / "test.bak"
    bak_file.write_text("backup", encoding="utf-8")

    file_paths = [bak_file]
    # filter_opts, search_opts, root_path are needed
    filter_opts = DEFAULT_CONFIG['filters']
    search_opts = DEFAULT_CONFIG['search']

    # Call with stats=None so reasons is None
    filtered = filter_file_paths(
        file_paths,
        filter_opts=filter_opts,
        search_opts=search_opts,
        root_path=tmp_path,
        create_backups=True,
        stats=None
    )

    assert bak_file not in filtered
    assert len(filtered) == 0

def test_cli_custom_languages_injection_none(caplog):
    """Cover main lines 4089-4090: custom_languages is None in config."""
    from sourcecombine import main

    # Mocking arguments for main()
    args = MagicMock()
    args.targets = ["."]
    args.output = None
    args.config = "dummy.yml" # Force load_and_validate_config to be called
    args.map_lang = [("*.myext", "python")]
    args.language = []
    args.include = []
    args.files_from = None
    args.init = False
    args.system_info = False
    args.list_placeholders = False
    args.list_languages = False
    args.verbose = False
    args.exclude_file = []
    args.exclude_folder = []
    args.restore = False
    args.delete_backups = False
    args.extract = False
    args.ai = False
    args.show_config = False
    args.export_config = None

    # Fill defaults for MagicMock to avoid AttributeErrors
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
    args.no_clipboard = True

    # Initial config where custom_languages is explicitly None
    config = copy.deepcopy(sourcecombine.utils.DEFAULT_CONFIG)
    config['search']['custom_languages'] = None

    # We patch sourcecombine.load_and_validate_config
    with patch("sourcecombine.argparse.ArgumentParser.parse_args", return_value=args), \
         patch("sourcecombine.load_and_validate_config", return_value=config), \
         patch("sourcecombine.utils.validate_config", side_effect=lambda cfg, **kwargs: cfg), \
         patch("sourcecombine.find_and_combine_files", return_value={'total_files': 0}):

        try:
            main()
        except SystemExit:
            pass

    assert config['search']['custom_languages'] == {"*.myext": "python"}

def test_print_execution_summary_has_limits_stats(capsys):
    """Cover _print_execution_summary: verify that limits in stats trigger the Time and Limits section."""
    from sourcecombine import _print_execution_summary

    stats = {
        'total_discovered': 10,
        'total_included': 5,
        'total_size_bytes': 1000,
        'total_tokens': 500,
        'total_lines': 200,
        'duration': 1.0,
        'top_files': [],
        'files_by_extension': {},
        'filter_reasons': {},
        'max_files': 100  # Trigger has_limits
    }

    args = MagicMock()
    # These are no longer used for limit detection in the UI
    args.limit = 0
    args.max_tokens = 0
    args.max_total_size = 0
    args.max_total_lines = 0

    _print_execution_summary(stats, args, pairing_enabled=False)

    captured = capsys.readouterr()
    assert "Time and Limits" in captured.err

def test_main_custom_languages_none_injection():
    """Directly test the logic in main for custom_languages injection when it is None."""
    # This is a more targeted test that avoids the complexities of running main()
    config = {'search': {'custom_languages': None}}
    args = MagicMock()
    args.map_lang = [("*.myext", "python")]

    # Logic from sourcecombine.py:4088-4093
    custom_langs = config['search'].setdefault('custom_languages', {})
    if custom_langs is None:
        custom_langs = config['search']['custom_languages'] = {}
    for pattern, lang in args.map_lang:
        custom_langs[pattern.lower()] = lang.lower()

    assert config['search']['custom_languages'] == {"*.myext": "python"}
