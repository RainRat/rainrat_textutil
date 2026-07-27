import sys
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))

from sourcecombine import main

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

def test_ai_preset_pyperclip_missing_warning(temp_cwd, mock_argv, caplog):
    with mock_argv(['.', '--ai']), \
         patch('importlib.util.find_spec', return_value=None), \
         patch('sourcecombine.find_and_combine_files') as mock_combine:

        mock_combine.return_value = {}
        main()

        warning_messages = [record.message for record in caplog.records if record.levelname == "WARNING"]

        expected_warning = (
            "The 'pyperclip' library is not installed. AI preset cannot automatically "
            "copy to the clipboard. Output will be saved to a file instead. "
            "To enable clipboard support, run: pip install pyperclip"
        )
        assert expected_warning in warning_messages
