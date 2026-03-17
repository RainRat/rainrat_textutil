import sys
import yaml
import io
import os
import copy
import pytest
from unittest.mock import patch, MagicMock
import sourcecombine
from sourcecombine import restore_backups

def test_main_show_config_converts_tuples_to_lists(capsys):
    with patch("sys.argv", ["sourcecombine.py", "--show-config"]):
        with pytest.raises(SystemExit) as excinfo:
            sourcecombine.main()
        assert excinfo.value.code == 0

    captured = capsys.readouterr()
    config = yaml.safe_load(captured.out)
    assert isinstance(config["search"]["effective_allowed_extensions"], list)

def test_main_injects_cli_options_into_missing_config_sections(capsys):
    base_config = {
        'search': {},
        'logging': {'level': 'INFO'},
        'pairing': {},
        'output': {}
    }

    with patch("sourcecombine.load_and_validate_config", return_value=base_config):
        with patch("sys.stdin", io.StringIO("")):
            with patch("sys.argv", [
                "sourcecombine.py", "--files-from", "-",
                "--max-total-size", "1MB",
                "--max-total-lines", "100",
                "-x", "skip.txt", "-X", "skip_dir", "-i", "include.txt",
                "--show-config"
            ]):
                with pytest.raises(SystemExit) as excinfo:
                    sourcecombine.main()
                assert excinfo.value.code == 0

    captured = capsys.readouterr()
    config = yaml.safe_load(captured.out)
    assert config["filters"]["max_total_size_bytes"] == 1024*1024
    assert config["filters"]["max_total_lines"] == 100
    assert "skip.txt" in config["filters"]["exclusions"]["filenames"]
    assert "skip_dir" in config["filters"]["exclusions"]["folders"]
    assert "include.txt" in config["filters"]["inclusion_groups"]["_cli_includes"]["filenames"]

def test_main_injects_cli_options_into_malformed_config_sections(capsys):
    base_config = {
        'search': {'root_folders': ['.']},
        'filters': {
            'exclusions': None,
            'inclusion_groups': None
        },
        'logging': {'level': 'INFO'},
        'pairing': {},
        'output': {}
    }

    with patch("sourcecombine.load_and_validate_config", return_value=base_config):
        with patch("sys.argv", [
            "sourcecombine.py", "-k", "dummy.yml",
            "-x", "skip.txt", "-X", "skip_dir", "-i", "include.txt",
            "--show-config"
        ]):
            with pytest.raises(SystemExit):
                sourcecombine.main()

    captured = capsys.readouterr()
    config = yaml.safe_load(captured.out)
    assert "skip.txt" in config["filters"]["exclusions"]["filenames"]
    assert "skip_dir" in config["filters"]["exclusions"]["folders"]
    assert "include.txt" in config["filters"]["inclusion_groups"]["_cli_includes"]["filenames"]

def test_main_injects_limits_when_filters_section_is_missing(capsys):
    base_config = {
        'search': {'root_folders': ['.']},
        'logging': {'level': 'INFO'},
        'pairing': {},
        'output': {}
    }

    with patch("sourcecombine.load_and_validate_config", return_value=base_config):
        with patch("sys.argv", [
            "sourcecombine.py", "-k", "dummy.yml",
            "--max-total-size", "1MB",
            "--max-total-lines", "100",
            "--show-config"
        ]):
            with pytest.raises(SystemExit):
                sourcecombine.main()

    captured = capsys.readouterr()
    config = yaml.safe_load(captured.out)
    assert config["filters"]["max_total_size_bytes"] == 1024*1024
    assert config["filters"]["max_total_lines"] == 100

def test_main_injects_max_depth_when_search_section_is_missing(capsys):
    base_config = {
        'filters': {},
        'logging': {'level': 'INFO'},
        'pairing': {},
        'output': {}
    }

    with patch("sourcecombine.load_and_validate_config", return_value=base_config):
        with patch("sys.argv", [
            "sourcecombine.py", "-k", "dummy.yml",
            "--max-depth", "2",
            "--show-config"
        ]):
            with pytest.raises(SystemExit):
                sourcecombine.main()

    captured = capsys.readouterr()
    config = yaml.safe_load(captured.out)
    assert config["search"]["max_depth"] == 2

def test_main_logs_error_with_traceback_on_invalid_time_in_verbose_mode(caplog):
    with patch("sys.argv", ["sourcecombine.py", "--since", "invalid-time", "--verbose"]):
        with pytest.raises(SystemExit) as excinfo:
            sourcecombine.main()
        assert excinfo.value.code == 1

    assert "Invalid time value" in caplog.text

def test_main_logs_error_with_traceback_on_invalid_size_in_verbose_mode(caplog):
    with patch("sys.argv", ["sourcecombine.py", "--max-size", "invalid-size", "--verbose"]):
        with pytest.raises(SystemExit) as excinfo:
            sourcecombine.main()
        assert excinfo.value.code == 1

    assert "Invalid size value" in caplog.text
    # Verify that the traceback (exc_info) is present in the log records
    assert any(record.exc_info is not None for record in caplog.records)

def test_main_exits_on_invalid_total_size_value(caplog):
    with patch("sys.argv", ["sourcecombine.py", "--max-total-size", "invalid-size"]):
        with pytest.raises(SystemExit) as excinfo:
            sourcecombine.main()
        assert excinfo.value.code == 1
    assert "Invalid size value" in caplog.text

def test_main_exits_on_invalid_size_value(caplog):
    with patch("sys.argv", ["sourcecombine.py", "--max-size", "invalid-size"]):
        with pytest.raises(SystemExit) as excinfo:
            sourcecombine.main()
        assert excinfo.value.code == 1

def test_main_shortcut_w_sets_xml_format(capsys):
    with patch("sys.argv", ["sourcecombine.py", "-w", "--show-config"]):
        with pytest.raises(SystemExit):
            sourcecombine.main()
    captured = capsys.readouterr()
    config = yaml.safe_load(captured.out)
    assert config["output"]["format"] == "xml"

def test_main_sets_in_place_processing_flags(capsys):
    with patch("sys.argv", ["sourcecombine.py", "--apply-in-place", "--create-backups", "--show-config"]):
        with pytest.raises(SystemExit):
            sourcecombine.main()
    captured = capsys.readouterr()
    config = yaml.safe_load(captured.out)
    assert config["processing"]["apply_in_place"] is True
    assert config["processing"]["create_backups"] is True

def test_main_sets_sort_and_reverse_flags(capsys):
    with patch("sys.argv", ["sourcecombine.py", "--sort", "size", "--reverse", "--show-config"]):
        with pytest.raises(SystemExit):
            sourcecombine.main()
    captured = capsys.readouterr()
    config = yaml.safe_load(captured.out)
    assert config["output"]["sort_by"] == "size"
    assert config["output"]["sort_reverse"] is True

def test_main_sets_max_lines(capsys):
    with patch("sys.argv", ["sourcecombine.py", "--max-lines", "5", "--show-config"]):
        with pytest.raises(SystemExit):
            sourcecombine.main()
    captured = capsys.readouterr()
    config = yaml.safe_load(captured.out)
    assert config["processing"]["max_lines"] == 5

def test_main_extract_auto_detects_markdown_file(tmp_path):
    combined_file = tmp_path / "combined_files.md"
    combined_file.write_text("## test.txt\n\n```\nhello\n```\n", encoding="utf-8")

    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        with patch("sys.argv", ["sourcecombine.py", "--extract", "--dry-run"]):
            with pytest.raises(SystemExit) as excinfo:
                sourcecombine.main()
            assert excinfo.value.code == 0
    finally:
        os.chdir(old_cwd)

def test_main_exits_when_pairing_to_stdout(caplog):
    config = copy.deepcopy(sourcecombine.DEFAULT_CONFIG)
    config['pairing']['enabled'] = True
    config['output']['file'] = None

    with patch("sourcecombine.load_and_validate_config", return_value=config):
        with patch("sys.argv", ["sourcecombine.py", "-k", "dummy.yml", "-o", "-", "--verbose"]):
            with pytest.raises(SystemExit) as excinfo:
                sourcecombine.main()
            assert excinfo.value.code == 1

    assert "cannot send output to your terminal when pairing files" in caplog.text

def test_restore_backups_defaults_to_current_directory_when_targets_are_empty():
    with patch("sourcecombine.Path.exists") as mock_exists:
        mock_exists.return_value = False
        restored, errors = restore_backups([])
        assert restored == 0
        assert errors == 0
        mock_exists.assert_any_call()
