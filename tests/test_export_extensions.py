import json
import os
import sys
from pathlib import Path
from unittest.mock import patch
import pytest

sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))

from sourcecombine import export_extensions, main


@pytest.fixture
def temp_cwd(tmp_path):
    original_cwd = os.getcwd()
    os.chdir(tmp_path)
    yield tmp_path
    os.chdir(original_cwd)


@pytest.fixture
def mock_argv():
    def _mock_argv(args):
        return patch.object(sys, 'argv', ['sourcecombine.py'] + args)
    return _mock_argv


def test_export_extensions_default_file(temp_cwd):
    export_extensions(None)
    out_file = temp_cwd / "extensions.json"
    assert out_file.is_file()
    data = json.loads(out_file.read_text(encoding="utf-8"))
    assert "total_mappings" in data
    assert "extensions" in data
    assert data["extensions"].get(".py") == "python"


def test_export_extensions_custom_file(temp_cwd):
    target = temp_cwd / "my_ext.json"
    export_extensions(str(target))
    assert target.is_file()
    data = json.loads(target.read_text(encoding="utf-8"))
    assert data["total_mappings"] > 0
    assert data["extensions"].get("dockerfile") == "dockerfile"


def test_export_extensions_directory_target(temp_cwd):
    target_dir = temp_cwd / "out_dir"
    target_dir.mkdir()
    export_extensions(str(target_dir))
    out_file = target_dir / "extensions.json"
    assert out_file.is_file()
    data = json.loads(out_file.read_text(encoding="utf-8"))
    assert data["total_mappings"] > 0


def test_export_extensions_stdout(capsys):
    export_extensions("-")
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["exported_to"] == "-"
    assert data["extensions"].get(".js") == "javascript"


def test_export_extensions_cli_main(temp_cwd, mock_argv):
    with mock_argv(['--export-ext']):
        with pytest.raises(SystemExit) as excinfo:
            main()
        assert excinfo.value.code == 0

    out_file = temp_cwd / "extensions.json"
    assert out_file.is_file()


def test_export_extensions_error_handling(temp_cwd, caplog):
    target_path = temp_cwd / "out.json"
    with patch("builtins.open", side_effect=OSError("Permission denied")):
        with pytest.raises(SystemExit) as excinfo:
            export_extensions(str(target_path))
        assert excinfo.value.code == 1
        assert "Could not export supported extensions" in caplog.text
