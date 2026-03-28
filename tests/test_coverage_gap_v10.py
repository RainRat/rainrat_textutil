import sys; import os; from pathlib import Path; sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))
import utils
from sourcecombine import should_include
from unittest.mock import patch

def test_should_include_virtual_content_language_detection_string():
    filter_opts = {}
    search_opts = {'allowed_languages': ['python']}
    virtual_content = "#!/usr/bin/python3\nprint('hello')"
    include, reason = should_include(
        None,
        Path("myscript"),
        filter_opts,
        search_opts,
        return_reason=True,
        virtual_content=virtual_content
    )
    assert include is True
    assert reason is None

def test_should_include_virtual_content_language_detection_bytes():
    filter_opts = {}
    search_opts = {'allowed_languages': ['python']}
    virtual_content = b"#!/usr/bin/python3\nprint('hello')"
    include, reason = should_include(
        None,
        Path("myscript"),
        filter_opts,
        search_opts,
        return_reason=True,
        virtual_content=virtual_content
    )
    assert include is True
    assert reason is None

def test_should_include_language_detection_oserror():
    filter_opts = {}
    search_opts = {'allowed_languages': ['python']}
    file_path = Path("myscript")

    with patch("builtins.open", side_effect=OSError("Permission denied")):
        with patch.object(Path, "is_file", return_value=True):
            include, reason = should_include(
                file_path,
                Path("myscript"),
                filter_opts,
                search_opts,
                return_reason=True
            )

    assert include is False
    assert reason == 'language_mismatch'

def test_detect_language_from_shebang_unknown():
    content = "#!/usr/bin/unknown-interpreter\n"
    lang = utils.detect_language_from_shebang(content)
    assert lang is None
