import sys, os; from pathlib import Path; sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))
import utils
from sourcecombine import should_include
from unittest.mock import MagicMock, patch

def test_should_include_virtual_content_language_detection():
    filter_opts = {}
    search_opts = {'allowed_languages': ['python']}
    relative_path = Path("script-no-ext")
    # Coverage for sourcecombine.py:505-509
    virtual_content = b"#!/usr/bin/env python3\nprint('hi')"

    # This should return True because it detects python from the virtual content
    assert should_include(
        None,
        relative_path,
        filter_opts,
        search_opts,
        virtual_content=virtual_content
    ) is True

def test_should_include_language_detection_oserror(tmp_path):
    filter_opts = {}
    search_opts = {'allowed_languages': ['python']}
    # File with no extension
    file_path = tmp_path / "bad-read"
    file_path.touch()
    relative_path = Path("bad-read")

    # Coverage for sourcecombine.py:514-515
    with patch("builtins.open", side_effect=OSError("Failed to open")):
        # Should return False (language_mismatch) because shebang detection fails and it falls back to "text"
        include, reason = should_include(
            file_path,
            relative_path,
            filter_opts,
            search_opts,
            return_reason=True
        )
        assert include is False
        assert reason == "language_mismatch"

def test_detect_language_from_shebang_unknown():
    # Coverage for utils.py:914
    content = "#!/usr/bin/unknown-interpreter\n"
    assert utils.detect_language_from_shebang(content) is None
