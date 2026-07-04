import sys
import os
import json
import hashlib
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open
import pytest
import logging
import io

# Ensure repo root is on path
sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))

import sourcecombine
import utils

def test_format_information_summary_colors():
    """Cover _format_information_summary lines 383-390, 407-412: colored status and summary combinations."""
    from sourcecombine import _format_information_summary, C_GREEN, C_YELLOW, C_RED, C_RESET

    with patch("sys.stdout.isatty", return_value=True), \
         patch("sys.stderr.isatty", return_value=True), \
         patch.dict(os.environ, {}, clear=True):

        # _format_information_summary returns with a leading space
        # A, ?? -> Green
        assert f" \x1b[32m[A]\x1b[0m" in _format_information_summary({'status': 'A'}, colored=True)
        assert f" \x1b[32m[??]\x1b[0m" in _format_information_summary({'status': '??'}, colored=True)

        # M, R -> Yellow
        assert f" \x1b[33m[M]\x1b[0m" in _format_information_summary({'status': 'M'}, colored=True)
        assert f" \x1b[33m[R]\x1b[0m" in _format_information_summary({'status': 'R'}, colored=True)

        # D -> Red
        assert f" \x1b[31m[D]\x1b[0m" in _format_information_summary({'status': 'D'}, colored=True)

        # Other -> Default
        assert " [X]" in _format_information_summary({'status': 'X'}, colored=True)
        assert "\x1b[32m" not in _format_information_summary({'status': 'X'}, colored=True)

    # Test colored=False with status (covers line 392)
    assert " [M]" in _format_information_summary({'status': 'M'}, colored=False)

    # Combinations (407-412)
    # status + summary
    res = _format_information_summary({'status': 'M', 'lines': 10}, colored=True)
    assert "[M]" in res and "10 lines" in res
    # summary only
    res = _format_information_summary({'lines': 10}, colored=True)
    assert "[M]" not in res and "10 lines" in res

def test_format_information_summary_more_parts():
    """Cover _format_information_summary lines 392-403: size, tokens, and plurals."""
    from sourcecombine import _format_information_summary

    meta = {
        'files': 2,
        'size': 1024,
        'lines': 100,
        'tokens': 50
    }
    res = _format_information_summary(meta)
    assert "2 files" in res
    assert "1.00 KB" in res
    assert "100 lines" in res
    assert "50 tokens" in res

    # Single forms
    meta = {
        'files': 1,
        'lines': 1,
        'tokens': 1
    }
    res = _format_information_summary(meta)
    assert "1 file" in res
    assert "1 line" in res
    assert "1 token" in res

def test_format_information_summary_empty():
    """Cover _format_information_summary line 412: empty meta."""
    from sourcecombine import _format_information_summary
    assert _format_information_summary({}) == ""

def test_main_list_languages(capsys):
    """Cover main lines 3924-3925: --list-languages branch."""
    from sourcecombine import main

    args = MagicMock()
    args.list_languages = True
    args.targets = ["."]
    # Minimum attributes to avoid AttributeError in main()
    args.config = None
    args.files_from = None
    args.init = False
    args.system_info = False
    args.list_placeholders = False
    args.verbose = False
    args.ai = False
    args.show_config = False
    args.restore = False
    args.delete_backups = False
    args.extract = False
    args.verify = False
    args.clean = False
    args.preview = False

    with patch("sourcecombine.argparse.ArgumentParser.parse_args", return_value=args):
        with pytest.raises(SystemExit) as cm:
            main()
        assert cm.value.code == 0

    captured = capsys.readouterr()
    assert "SUPPORTED LANGUAGES" in captured.out
    assert "python" in captured.out

def test_main_list_placeholders(capsys):
    """Cover main lines 3924-3925: --list-placeholders branch in main."""
    from sourcecombine import main

    args = MagicMock()
    args.list_placeholders = True
    args.targets = ["."]
    args.config = None
    args.files_from = None
    args.init = False
    args.system_info = False
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

    with patch("sourcecombine.argparse.ArgumentParser.parse_args", return_value=args):
        with pytest.raises(SystemExit) as cm:
            main()
        assert cm.value.code == 0

    captured = capsys.readouterr()
    assert "=== TEMPLATE PLACEHOLDERS ===" in captured.out

def test_verify_files_repair_missing_with_mtime(tmp_path, capsys):
    """Cover verify_files line 4768: missing file repair with modification time."""
    from sourcecombine import verify_files

    root = tmp_path / "root"
    root.mkdir()

    combined_data = [{
        "path": "newfile.txt",
        "content": "data",
        "size_bytes": 4,
        "modified": 123456789.0
    }]
    sources = [("test.json", json.dumps(combined_data))]

    results = verify_files(sources, root_folder=root, repair=True)

    assert results['repaired'] == 1
    target = root / "newfile.txt"
    assert target.exists()
    assert target.stat().st_mtime == 123456789.0

def test_verify_files_repair_missing_oserror(capsys):
    """Cover verify_files lines 4768, 4771-4773: OSError during missing file repair."""
    from sourcecombine import verify_files

    root = Path("non_existent_root_because_of_mock")
    combined_data = [{"path": "file.txt", "content": "data", "size_bytes": 4}]
    sources = [("test.json", json.dumps(combined_data))]

    with patch("pathlib.Path.mkdir", side_effect=OSError("Permission denied")):
        results = verify_files(sources, root_folder=root, repair=True)

    assert results['repaired'] == 0
    assert results['missing'] == 1
    captured = capsys.readouterr()
    assert "[ERROR]" in captured.out
    assert "failed to repair" in captured.out

def test_verify_files_repair_hash_mismatch(tmp_path, capsys):
    """Cover verify_files lines 4789-4801: hash mismatch repair (dry_run, success, error)."""
    from sourcecombine import verify_files

    root = tmp_path / "root"
    root.mkdir()
    f = root / "mismatch.txt"
    f.write_text("old content")
    expected_content = "new content"
    expected_hash = hashlib.sha256(expected_content.encode()).hexdigest()

    combined_data = [{
        "path": "mismatch.txt",
        "content": expected_content,
        "sha256": expected_hash,
        "modified": 123456789.0
    }]
    sources = [("test.json", json.dumps(combined_data))]

    # 1. Dry run (4789-4791)
    results = verify_files(sources, root_folder=root, repair=True, dry_run=True)
    assert results['repaired'] == 1
    assert f.read_text() == "old content"
    assert "would fix hash mismatch" in capsys.readouterr().out

    # 2. Repair success (4793-4798)
    results = verify_files(sources, root_folder=root, repair=True)
    assert results['repaired'] == 1
    assert f.read_text() == "new content"
    assert "fixed hash mismatch" in capsys.readouterr().out

    # 3. Repair OSError (4800-4801)
    f.write_text("wrong again")
    with patch("pathlib.Path.write_text", side_effect=OSError("Locked")):
        results = verify_files(sources, root_folder=root, repair=True)
    assert results['repaired'] == 0
    assert results['mismatches'] == 1
    assert "failed to repair" in capsys.readouterr().out

def test_verify_files_repair_content_mismatch(tmp_path, capsys):
    """Cover verify_files lines 4823-4824, 4829, 4832-4834: content mismatch repair."""
    from sourcecombine import verify_files

    root = tmp_path / "root"
    root.mkdir()
    f = root / "mismatch.txt"
    f.write_text("old content")
    expected_content = "new content"

    # No hash, just content
    combined_data = [{
        "path": "mismatch.txt",
        "content": expected_content,
        "modified": 123456789.0
    }]
    sources = [("test.json", json.dumps(combined_data))]

    # 1. Dry run (4823-4825)
    results = verify_files(sources, root_folder=root, repair=True, dry_run=True)
    assert results['repaired'] == 1
    assert f.read_text() == "old content"
    assert "would fix content mismatch" in capsys.readouterr().out

    # 2. Repair success (4827-4831)
    results = verify_files(sources, root_folder=root, repair=True)
    assert results['repaired'] == 1
    assert f.read_text() == "new content"
    assert "fixed content mismatch" in capsys.readouterr().out

    # 3. Repair OSError (4833-4834)
    f.write_text("wrong again")
    with patch("pathlib.Path.write_text", side_effect=OSError("Locked")):
        results = verify_files(sources, root_folder=root, repair=True)
    assert results['repaired'] == 0
    assert results['mismatches'] == 1
    assert "failed to repair" in capsys.readouterr().out

def test_print_execution_summary_status_indicator(capsys):
    """Cover _print_execution_summary lines 5757-5759: status indicator in table."""
    from sourcecombine import _print_execution_summary

    stats = {
        'total_discovered': 1,
        'total_included': 1,
        'total_size_bytes': 100,
        'token_count': 10,
        'total_lines': 5,
        'duration': 0.1,
        'top_files': [(10, 100, "file.txt", "M")], # status "M"
        'files_by_language': {".txt": 1},
        'tokens_by_language': {".txt": 10},
        'size_by_language': {".txt": 100},
        'total_tokens': 10,
        'filter_reasons': {}
    }

    args = MagicMock()
    args.limit = 0
    args.max_tokens = 0
    args.max_total_size = 0
    args.max_total_lines = 0

    with patch("sys.stderr", new=io.StringIO()) as mock_stderr:
        _print_execution_summary(stats, args, pairing_enabled=False)
        output = mock_stderr.getvalue()

    assert "[M]" in output

    # Also test with [??] to cover visible_len = 4 branch
    stats['top_files'] = [(10, 100, "file.txt", "??")]
    with patch("sys.stderr", new=io.StringIO()) as mock_stderr:
        _print_execution_summary(stats, args, pairing_enabled=False)
        output = mock_stderr.getvalue()
    assert "[??]" in output

def test_utils_load_yaml_config_no_yaml():
    """Cover utils.py line 208: load_yaml_config when yaml is None."""
    with patch("utils.yaml", None):
        with pytest.raises(utils.InvalidConfigError) as excinfo:
            utils.load_yaml_config("any.yml")
        assert "PyYAML" in str(excinfo.value)

def test_utils_yaml_import_error():
    """Attempt to cover utils.py lines 17-18: ImportError for yaml."""
    with patch.dict(sys.modules, {'yaml': None}):
        if 'utils' in sys.modules:
            import importlib
            importlib.reload(utils)
            assert utils.yaml is None
    import importlib
    importlib.reload(utils)
    assert utils.yaml is not None

def test_utils_tiktoken_import_error():
    """Attempt to cover utils.py lines 22-23: ImportError for tiktoken."""
    with patch.dict(sys.modules, {'tiktoken': None}):
        if 'utils' in sys.modules:
            import importlib
            importlib.reload(utils)
            assert utils.tiktoken is None
    import importlib
    importlib.reload(utils)
