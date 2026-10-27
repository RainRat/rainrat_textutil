import json
import pytest
from unittest.mock import patch
from sourcecombine import export_extensions, main
import utils


def test_export_extensions_stdout(capsys):
    export_extensions('-')
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["exported_to"] == "-"
    expected_total = len(utils.EXTENSION_TO_LANG) + len(utils.FILENAME_TO_LANG)
    assert data["total_extensions"] == expected_total
    assert data["extensions"][".py"] == "python"
    assert data["extensions"]["package.json"] == "json"


def test_export_extensions_file(tmp_path):
    target_file = tmp_path / "custom_extensions.json"
    export_extensions(str(target_file))
    assert target_file.is_file()
    with open(target_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["exported_to"] == str(target_file.resolve())
    expected_total = len(utils.EXTENSION_TO_LANG) + len(utils.FILENAME_TO_LANG)
    assert data["total_extensions"] == expected_total
    assert data["extensions"][".rs"] == "rust"


def test_export_extensions_default_filename(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    export_extensions(None)
    expected_file = tmp_path / "extensions.json"
    assert expected_file.is_file()
    with open(expected_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["exported_to"] == str(expected_file.resolve())


def test_export_extensions_directory(tmp_path):
    target_dir = tmp_path / "ext_dir"
    target_dir.mkdir()
    export_extensions(str(target_dir))
    expected_file = target_dir / "extensions.json"
    assert expected_file.is_file()
    with open(expected_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["exported_to"] == str(expected_file.resolve())


def test_export_extensions_oserror_handling(tmp_path):
    invalid_path = tmp_path / "out.json"
    with patch("builtins.open", side_effect=OSError("Permission denied")):
        with pytest.raises(SystemExit) as exc_info:
            export_extensions(str(invalid_path))
        assert exc_info.value.code == 1


def test_main_export_extensions_cli_flag(tmp_path):
    target_file = tmp_path / "out_ext.json"
    test_args = ["sourcecombine.py", "--export-extensions", str(target_file)]
    with patch("sys.argv", test_args):
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0
    assert target_file.is_file()


def test_main_export_ext_alias_cli_flag(tmp_path):
    target_file = tmp_path / "out_ext_alias.json"
    test_args = ["sourcecombine.py", "--export-ext", str(target_file)]
    with patch("sys.argv", test_args):
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0
    assert target_file.is_file()


def test_main_export_extensions_conflict_with_files_from():
    test_args = ["sourcecombine.py", "--export-extensions", "--files-from", "some_list.txt"]
    with patch("sys.argv", test_args):
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1
