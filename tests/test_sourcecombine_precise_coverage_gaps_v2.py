import sys
import os
import shutil
import json
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))

import sourcecombine
import utils


def test_get_primary_metric_combinations():
    assert sourcecombine._get_primary_metric(True, True) == "tokens"
    assert sourcecombine._get_primary_metric(True, False) == "tokens"
    assert sourcecombine._get_primary_metric(False, True) == "lines"
    assert sourcecombine._get_primary_metric(False, False) == "size"


def test_explain_paths_with_config_none(tmp_path, capsys):
    test_file = tmp_path / "dummy.py"
    test_file.write_text("print('hello')")

    sourcecombine.explain_paths([str(test_file)], config=None, json_format=True)
    captured = capsys.readouterr()
    results = json.loads(captured.out)

    assert len(results) == 1
    assert results[0]["exists"] is True
    assert results[0]["included"] is True


def test_explain_paths_stat_os_error(tmp_path, capsys):
    test_file = tmp_path / "dummy.py"
    test_file.write_text("print('hello')")

    config = utils.DEFAULT_CONFIG.copy()
    config["search"] = {
        "root_folders": [str(tmp_path)],
        "effective_allowed_extensions": (".py",),
        "effective_exclude_extensions": (),
    }

    original_stat = Path.stat

    import inspect

    def mock_stat(self, *args, **kwargs):
        if self.name == "dummy.py":
            f = inspect.currentframe().f_back
            while f:
                if f.f_code.co_name == "explain_paths":
                    ctx = inspect.getframeinfo(f).code_context
                    if ctx and "stat = file_path.stat()" in ctx[0]:
                        raise OSError("Disk failure")
                    break
                f = f.f_back
        return original_stat(self, *args, **kwargs)

    with patch.object(Path, "stat", autospec=True, side_effect=mock_stat):
        sourcecombine.explain_paths([str(test_file)], config=config, json_format=True)

    captured = capsys.readouterr()
    results = json.loads(captured.out)

    assert len(results) == 1
    assert results[0]["exists"] is True
    assert results[0]["metadata"]["size_bytes"] is None


def test_explain_paths_read_file_exception(tmp_path, capsys):
    test_file = tmp_path / "dummy.py"
    test_file.write_text("print('hello')")

    config = utils.DEFAULT_CONFIG.copy()
    config["search"] = {
        "root_folders": [str(tmp_path)],
        "effective_allowed_extensions": (".py",),
        "effective_exclude_extensions": (),
    }

    with patch("sourcecombine.read_file_best_effort", side_effect=Exception("Read failure")):
        sourcecombine.explain_paths([str(test_file)], config=config, json_format=True)

    captured = capsys.readouterr()
    results = json.loads(captured.out)

    assert len(results) == 1
    assert results[0]["exists"] is True
    assert results[0]["metadata"]["lines"] is None
    assert results[0]["metadata"]["tokens"] is None


def test_create_backup_if_enabled_os_error(tmp_path):
    test_file = tmp_path / "dummy.txt"
    test_file.write_text("original content")

    with patch("shutil.copy2", side_effect=OSError("Write permission denied")):
        with pytest.raises(utils.InvalidConfigError) as exc_info:
            sourcecombine._create_backup_if_enabled(test_file, create_backups=True)

    assert "Failed to create backup for" in str(exc_info.value)
