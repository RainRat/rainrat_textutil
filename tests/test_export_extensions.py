import json
import pytest
from sourcecombine import export_extensions, main


def test_export_extensions_stdout(capsys):
    export_extensions('-')
    captured = capsys.readouterr()
    assert captured.out
    data = json.loads(captured.out)
    assert data['exported_to'] == '-'
    assert data['total'] > 0
    assert 'extensions' in data
    assert data['extensions']['.py'] == 'python'
    assert data['extensions']['makefile'] == 'makefile'


def test_export_extensions_file(tmp_path):
    target_file = tmp_path / "custom_ext.json"
    export_extensions(str(target_file))

    assert target_file.exists()
    content = target_file.read_text(encoding='utf-8')
    data = json.loads(content)
    assert data['total'] > 0
    assert data['extensions']['.js'] == 'javascript'


def test_export_extensions_directory(tmp_path):
    target_dir = tmp_path / "out_dir"
    target_dir.mkdir()

    export_extensions(str(target_dir))
    expected_file = target_dir / "extensions.json"
    assert expected_file.exists()
    data = json.loads(expected_file.read_text(encoding='utf-8'))
    assert data['extensions']['.go'] == 'go'


def test_export_extensions_oserror_handling(tmp_path):
    invalid_path = tmp_path / "nonexistent_dir" / "nested" / "file.json"
    # We test that OSError causes sys.exit(1)
    with pytest.raises(SystemExit) as exc_info:
        import unittest.mock as mock
        with mock.patch("builtins.open", side_effect=OSError("Permission denied")):
            export_extensions(str(tmp_path / "file.json"))
    assert exc_info.value.code == 1


def test_main_export_extensions_cli_flag(tmp_path, capsys, monkeypatch):
    target_file = tmp_path / "exported_extensions.json"
    monkeypatch.setattr("sys.argv", ["sourcecombine", "--export-extensions", str(target_file)])

    with pytest.raises(SystemExit) as exc_info:
        main()
    assert exc_info.value.code == 0

    assert target_file.exists()
    data = json.loads(target_file.read_text(encoding='utf-8'))
    assert data['extensions']['.rs'] == 'rust'


def test_main_export_extensions_conflict_with_files_from(tmp_path, monkeypatch):
    monkeypatch.setattr("sys.argv", ["sourcecombine", "--export-extensions", "-", "--files-from", "list.txt"])

    with pytest.raises(SystemExit) as exc_info:
        main()
    assert exc_info.value.code == 1
