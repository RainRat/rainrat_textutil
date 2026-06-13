import sys; import os; from pathlib import Path; sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))

import json
import logging
from pathlib import Path
from unittest.mock import patch, MagicMock
import urllib.error
import pytest

from sourcecombine import main, __version__

def test_extract_from_url(tmp_path, caplog):
    caplog.set_level(logging.INFO)
    output_dir = tmp_path / "extracted"
    url = "https://example.com/combined.json"

    data = [
        {"path": "remote.py", "content": "print('remote')"}
    ]
    json_content = json.dumps(data).encode('utf-8')

    mock_response = MagicMock()
    mock_response.read.return_value = json_content
    mock_response.__enter__.return_value = mock_response

    with patch("urllib.request.urlopen", return_value=mock_response) as mock_urlopen, \
         patch("urllib.request.Request") as mock_request_class, \
         patch("sys.argv", ["sourcecombine.py", "--extract", url, "--output", str(output_dir)]), \
         patch("sys.exit") as mock_exit:

        # Mock Request to capture user agent
        mock_request_instance = MagicMock()
        mock_request_class.return_value = mock_request_instance

        main()

        # Verify URL was called
        mock_request_class.assert_called_once()
        args, kwargs = mock_request_class.call_args
        assert args[0] == url
        assert kwargs['headers']['User-Agent'] == f"SourceCombine/{__version__}"

        # Verify extraction
        assert (output_dir / "remote.py").read_text(encoding="utf-8") == "print('remote')"
        mock_exit.assert_called_with(0)

def test_verify_from_url(tmp_path, capsys):
    url = "https://example.com/manifest.json"

    # Create a file to verify
    test_file_rel = "to_verify.txt"
    test_file = tmp_path / test_file_rel
    test_file.write_text("content", encoding="utf-8")

    data = [
        {"path": test_file_rel, "content": "content"}
    ]
    json_content = json.dumps(data).encode('utf-8')

    mock_response = MagicMock()
    mock_response.read.return_value = json_content
    mock_response.__enter__.return_value = mock_response

    # Change current working directory to tmp_path for the test
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        with patch("urllib.request.urlopen", return_value=mock_response), \
             patch("sys.argv", ["sourcecombine.py", "--verify", url]), \
             patch("sys.exit") as mock_exit:

            main()

            captured = capsys.readouterr()
            assert "Matches:    1/1" in captured.out
            mock_exit.assert_called_with(0)
    finally:
        os.chdir(old_cwd)

def test_url_fetch_error(tmp_path, caplog):
    caplog.set_level(logging.WARNING)
    url = "https://example.com/missing.json"

    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("Not Found")), \
         patch("sys.argv", ["sourcecombine.py", "--extract", url, "--output", str(tmp_path)]):

        with pytest.raises(SystemExit):
            main()

        assert f"Could not read URL {url}" in caplog.text

def test_url_invalid_scheme(tmp_path, caplog):
    caplog.set_level(logging.WARNING)
    # We only support http/https
    url = "ftp://example.com/data.json"

    with patch("sys.argv", ["sourcecombine.py", "--extract", url, "--output", str(tmp_path)]):
        # It should try to treat it as a file path and fail
        with pytest.raises(SystemExit):
            main()

        assert "Extraction target not found: ftp://example.com/data.json" in caplog.text
