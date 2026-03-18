import os
import sys
import logging
import pytest
import importlib
from pathlib import Path
from unittest.mock import patch, MagicMock
import sourcecombine
import utils

def test_convert_to_json_friendly_path():
    # Covers sourcecombine.py line 35
    path = Path("some/path")
    result = sourcecombine._convert_to_json_friendly(path)
    assert result == "some/path"

def test_write_json_summary_oserror(caplog):
    # Covers sourcecombine.py line 66
    stats = {"total_files": 1}
    with patch("pathlib.Path.mkdir"), \
         patch("pathlib.Path.write_text", side_effect=OSError("Disk full")):
        sourcecombine._write_json_summary(stats, "fail.json")
    assert "Failed to write JSON summary to 'fail.json': Disk full" in caplog.text

def test_silent_progress_methods():
    # Covers sourcecombine.py line 195, 201, 204
    sp = sourcecombine._SilentProgress()
    sp.set_postfix(some="data")
    sp.close()
    with sp as same_sp:
        assert same_sp is sp

def test_main_invalid_total_size_verbose(caplog):
    # Covers sourcecombine.py line 2732
    with patch("sys.argv", ["sourcecombine.py", "--max-total-size", "invalid", "--verbose"]), \
         patch("sourcecombine.load_and_validate_config", return_value=sourcecombine.DEFAULT_CONFIG):
        with pytest.raises(SystemExit) as excinfo:
            sourcecombine.main()
        assert excinfo.value.code == 1
    assert "Invalid size value" in caplog.text
    assert any(record.exc_info is not None for record in caplog.records)

def test_main_json_summary_flag(capsys):
    # Covers sourcecombine.py line 2792
    with patch("sys.argv", ["sourcecombine.py", "--json-summary", "summary.json", "--show-config"]), \
         patch("sourcecombine.load_and_validate_config", return_value=sourcecombine.DEFAULT_CONFIG):
        with pytest.raises(SystemExit):
            sourcecombine.main()
    captured = capsys.readouterr()
    assert "summary_json: summary.json" in captured.out

def test_utils_tiktoken_import_failure():
    # Covers utils.py lines 12-13
    import builtins
    original_import = builtins.__import__

    def mocked_import(name, *args, **kwargs):
        if name == 'tiktoken':
            raise ImportError("Mocked import error")
        return original_import(name, *args, **kwargs)

    with patch('builtins.__import__', side_effect=mocked_import):
        # Reload utils to trigger the try-except block
        importlib.reload(utils)
        assert utils.tiktoken is None

    # Restore utils to its original state for other tests
    importlib.reload(utils)

def test_validate_processing_create_backups_non_bool():
    # Covers utils.py line 513
    config = {'processing': {'create_backups': 'not-a-bool'}}
    # Use utils.InvalidConfigError directly to avoid issues with reloaded modules
    with pytest.raises(utils.InvalidConfigError) as excinfo:
        utils.validate_config(config)
    assert "'processing.create_backups' must be true or false" in str(excinfo.value)

def test_write_json_summary_none_stats():
    # Extra coverage for deepcopy and keys if stats is None or similar
    # Though stats is usually a dict, let's see
    sourcecombine._write_json_summary({}, None) # Should return immediately

def test_write_json_summary_full_branches(caplog):
    # Covers sourcecombine.py lines 46, 48, 50, 64
    stats = {"total_files": 1}
    # Use side_effect=lambda x: x to make mock_convert return a JSON serializable dict
    with patch("sourcecombine._convert_to_json_friendly", side_effect=lambda x: x) as mock_convert:
        # Mocking to skip the actual write but reach the lines
        with patch("pathlib.Path.write_text"), patch("pathlib.Path.mkdir"):
            sourcecombine._write_json_summary(stats, "test.json", duration=1.0, source_desc="src", destination_desc="dest")

            args, _ = mock_convert.call_args
            summary = args[0]
            assert summary['duration_seconds'] == 1.0
            assert summary['source'] == "src"
            assert summary['destination'] == "dest"

    # Also verify line 64 (logging.info)
    with patch("pathlib.Path.write_text"), patch("pathlib.Path.mkdir"):
        sourcecombine._write_json_summary(stats, "test_info.json")
    assert "JSON execution summary saved to 'test_info.json'." in caplog.text

def test_write_json_summary_stderr(capsys):
    # Covers sourcecombine.py lines 57-59
    stats = {"total_files": 1}
    sourcecombine._write_json_summary(stats, "-")
    captured = capsys.readouterr()
    # It writes to stderr
    assert "--- JSON Execution Summary ---" in captured.err
    assert "total_files" in captured.err
