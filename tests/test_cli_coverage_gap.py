import pytest
import sys
import logging
from pathlib import Path
from unittest.mock import patch, MagicMock
from sourcecombine import (
    xml_escape,
    CLILogFormatter,
    _pair_files,
    main,
    print_system_info,
    extract_files
)

def test_xml_escape_empty_and_none():
    assert xml_escape("") == ""
    assert xml_escape(None) == ""

def test_cli_log_formatter_exc_and_stack():
    formatter = CLILogFormatter()

    try:
        raise ValueError("test exception")
    except ValueError:
        exc_info = sys.exc_info()

    record = logging.LogRecord(
        name="test", level=logging.ERROR, pathname="test.py", lineno=1,
        msg="Error message", args=(), exc_info=exc_info
    )
    formatted = formatter.format(record)
    assert "ValueError: test exception" in formatted

    record = logging.LogRecord(
        name="test", level=logging.ERROR, pathname="test.py", lineno=1,
        msg="Error message", args=(), exc_info=None
    )
    record.stack_info = "Stack trace info"
    formatted = formatter.format(record)
    assert "Stack trace info" in formatted

def test_pair_files_unrooted_path_value_error_branch():
    root_path = Path("/root")
    filtered_paths = [Path("/other/file.cpp")]

    result = _pair_files(filtered_paths, (), (), False, root_path=root_path)
    assert result == {}

def test_main_config_initialization_with_since_flag():
    with patch("sourcecombine.validate_config"):
        with patch.object(sys, "argv", ["sourcecombine.py", "config.yml", "--since", "1d", "-o", "out.txt"]):
            with patch("sourcecombine.Path.is_dir", return_value=False):
                config_no_filters = {"search": {"root_folders": ["."]}, "output": {}}
                with patch("sourcecombine.load_and_validate_config", return_value=config_no_filters):
                    with patch("sourcecombine.find_and_combine_files", return_value={}) as mock_combine:
                        main()
                        config = mock_combine.call_args[0][0]
                        assert 'filters' in config
                        assert 'modified_since' in config['filters']

def test_main_config_initialization_with_compact_flag():
    with patch("sourcecombine.validate_config"):
        with patch.object(sys, "argv", ["sourcecombine.py", "config.yml", "--compact", "-o", "out.txt"]):
            with patch("sourcecombine.Path.is_dir", return_value=False):
                config_no_proc = {"search": {"root_folders": ["."]}, "output": {}}
                with patch("sourcecombine.load_and_validate_config", return_value=config_no_proc):
                    with patch("sourcecombine.find_and_combine_files", return_value={}) as mock_combine:
                        main()
                        config = mock_combine.call_args[0][0]
                        assert 'processing' in config
                        assert config['processing']['compact_whitespace'] is True

def test_main_system_info_exit_behavior():
    with patch.object(sys, "argv", ["sourcecombine.py", "--system-info"]):
        with patch("sourcecombine.print_system_info") as mock_info:
            with pytest.raises(SystemExit) as exc:
                main()
            assert exc.value.code == 0
            mock_info.assert_called_once()

def test_extract_files_invalid_path_error_handling(caplog):
    caplog.set_level(logging.WARNING)
    content = "--- test.txt ---\ncontent\n--- end test.txt ---"

    original_resolve = Path.resolve

    def side_effect(self, *args, **kwargs):
        if str(self) == "out":
            return original_resolve(self, *args, **kwargs)
        raise ValueError("invalid path")

    with patch("sourcecombine.Path.resolve", side_effect):
        extract_files(content, Path("out"))

    assert "Skipping invalid path" in caplog.text

def test_print_system_info_with_and_without_optional_dependencies(capsys):
    with patch("importlib.util.find_spec", side_effect=lambda name: MagicMock() if name == "tiktoken" else None):
        print_system_info()

    captured = capsys.readouterr()
    assert "SourceCombine System Information" in captured.out
    assert "tiktoken" in captured.out
    assert "Installed" in captured.out
    assert "pyperclip" in captured.out
    assert "Not found" in captured.out
