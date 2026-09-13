import sys, os; from pathlib import Path; sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))
import json
import tempfile
import pytest
from unittest.mock import patch

import utils
import sourcecombine


def test_print_ignore_patterns_json_query_filtering(capsys, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    ignore_file = tmp_path / ".sourcecombineignore"
    ignore_file.write_text("*.log\ntmp/*\n")

    sourcecombine.print_ignore_patterns(query="log", json_format=True)
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert "ignore_patterns" in data
    assert data["total"] == 1
    assert "Ignore File (.sourcecombineignore)" in data["ignore_patterns"]
    assert data["ignore_patterns"]["Ignore File (.sourcecombineignore)"] == ["*.log"]


def test_filter_file_paths_excluded_bak_reasons_and_both_exclusions_return():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        bak_file = tmp / "test.bak"
        bak_file.write_text("bak content")

        reasons = {}
        filtered, size_excluded, all_exclusions = sourcecombine.filter_file_paths(
            [bak_file],
            filter_opts={},
            search_opts={},
            root_path=tmp,
            create_backups=True,
            record_size_exclusions=True,
            record_all_exclusions=True,
            stats={"filter_reasons": reasons},
        )
        assert len(filtered) == 0
        assert len(size_excluded) == 0
        assert reasons.get("excluded_bak") == 1
        assert len(all_exclusions) == 1
        assert all_exclusions[0] == (bak_file, "excluded_bak")


def test_find_and_combine_files_list_excluded_with_record_size_exclusions():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        p1 = tmp / "file1.txt"
        p1.write_text("hello")
        p2 = tmp / "file2.txt"
        p2.write_text("x" * 100)
        out_file = tmp / "out.txt"

        cfg = utils.DEFAULT_CONFIG.copy()
        cfg["search"] = {"root_folder": str(tmp), "ignore_files": []}
        cfg["pairing"] = {"enabled": False}
        cfg["filters"] = {"max_file_size": 10}
        cfg["output"] = {"max_size_placeholder": "[TOO LARGE]"}

        result = sourcecombine.find_and_combine_files(
            cfg,
            str(out_file),
            dry_run=True,
            list_excluded=True,
            explicit_files=[p1, p2],
        )
        assert result is not None


def test_cli_list_ignores_default_config_file_found(capsys, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    default_cfg = tmp_path / "sourcecombine.yml"
    default_cfg.write_text("search:\n  ignore_files: []\n")

    with patch("sys.argv", ["sourcecombine", "--list-ignores"]):
        with pytest.raises(SystemExit) as exc:
            sourcecombine.main()
        assert exc.value.code == 0


def test_cli_list_ignores_config_not_found_error(capsys, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    with patch("sys.argv", ["sourcecombine", "--list-ignores", "-k", "nonexistent_cfg.yml"]):
        with pytest.raises(SystemExit) as exc:
            sourcecombine.main()
        assert exc.value.code == 1


def test_cli_list_ignores_when_ignore_files_is_none_in_config(capsys, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    custom_ignore = tmp_path / "custom.ignore"
    custom_ignore.write_text("*.tmp\n")

    cfg = utils.DEFAULT_CONFIG.copy()
    cfg["search"] = {"ignore_files": None}

    with patch("sourcecombine.load_and_validate_config", return_value=cfg):
        with patch("sys.argv", ["sourcecombine", "--list-ignores", "-k", "cfg.yml", "--ignore-file", str(custom_ignore)]):
            with pytest.raises(SystemExit) as exc:
                sourcecombine.main()
            assert exc.value.code == 0

    captured = capsys.readouterr()
    assert "*.tmp" in captured.out


def test_get_project_identity_gradle_settings_exception_handling():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        settings = tmp / "settings.gradle"
        settings.write_text("rootProject.name = 'mygradle'\n")

        with patch.object(Path, "read_text", side_effect=OSError("Read error")):
            ident = utils.get_project_identity(tmp)
            assert ident is not None
