import sys
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest
import sourcecombine

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

def test_cli_recursive_by_default(temp_cwd, mock_argv):
    root_file = temp_cwd / "root_file.txt"
    root_file.write_text("root file content", encoding="utf-8")

    sub_dir = temp_cwd / "sub"
    sub_dir.mkdir()
    sub_file = sub_dir / "sub_file.txt"
    sub_file.write_text("sub file content", encoding="utf-8")

    with mock_argv([str(temp_cwd), "--dry-run"]):
        with patch('sourcecombine.find_and_combine_files') as mock_combine:
            mock_combine.return_value = {}
            sourcecombine.main()

            args, _ = mock_combine.call_args
            config = args[0]
            assert config['search']['recursive'] is True

def test_cli_no_recursive_flag_disables_recursion(temp_cwd, mock_argv):
    root_file = temp_cwd / "root_file.txt"
    root_file.write_text("root file content", encoding="utf-8")

    sub_dir = temp_cwd / "sub"
    sub_dir.mkdir()
    sub_file = sub_dir / "sub_file.txt"
    sub_file.write_text("sub file content", encoding="utf-8")

    with mock_argv([str(temp_cwd), "--no-recursive", "--dry-run"]):
        with patch('sourcecombine.find_and_combine_files') as mock_combine:
            mock_combine.return_value = {}
            sourcecombine.main()

            args, _ = mock_combine.call_args
            config = args[0]
            assert config['search']['recursive'] is False

def test_no_recursive_file_scanning_omits_subdirectories(temp_cwd, mock_argv):
    root_file = temp_cwd / "root_file.txt"
    root_file.write_text("root file content", encoding="utf-8")

    sub_dir = temp_cwd / "sub"
    sub_dir.mkdir()
    sub_file = sub_dir / "sub_file.txt"
    sub_file.write_text("sub file content", encoding="utf-8")

    out_file = temp_cwd / "output.txt"

    with mock_argv([str(temp_cwd), "--no-recursive", "-o", str(out_file)]):
        sourcecombine.main()

    assert out_file.exists()
    content = out_file.read_text(encoding="utf-8")
    assert "root_file.txt" in content
    assert "sub_file.txt" not in content
