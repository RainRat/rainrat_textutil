import json
import pytest
from unittest.mock import patch
from sourcecombine import export_presets, main


def test_export_presets_stdout(capsys):
    export_presets('-')
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["exported_to"] == "-"
    assert data["total_presets"] == 3
    assert "ai" in data["presets"]
    assert "analyze" in data["presets"]
    assert "review" in data["presets"]


def test_export_presets_file(tmp_path):
    target_file = tmp_path / "custom_presets.json"
    export_presets(str(target_file))
    assert target_file.is_file()
    with open(target_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["exported_to"] == str(target_file.resolve())
    assert data["total_presets"] == 3
    assert "ai" in data["presets"]


def test_export_presets_directory(tmp_path):
    target_dir = tmp_path / "presets_dir"
    target_dir.mkdir()
    export_presets(str(target_dir))
    expected_file = target_dir / "presets.json"
    assert expected_file.is_file()
    with open(expected_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["exported_to"] == str(expected_file.resolve())


def test_export_presets_oserror_handling(tmp_path):
    invalid_path = tmp_path / "non_existent_folder" / "file.json"
    with patch("builtins.open", side_effect=OSError("Permission denied")):
        with pytest.raises(SystemExit) as exc_info:
            export_presets(str(invalid_path))
        assert exc_info.value.code == 1


def test_main_export_presets_cli_flag(tmp_path, capsys):
    target_file = tmp_path / "out_presets.json"
    test_args = ["sourcecombine.py", "--export-presets", str(target_file)]
    with patch("sys.argv", test_args):
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0
    assert target_file.is_file()


def test_main_export_presets_conflict_with_files_from(tmp_path):
    test_args = ["sourcecombine.py", "--export-presets", "--files-from", "some_list.txt"]
    with patch("sys.argv", test_args):
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1
