import json
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
import sourcecombine
import utils

@pytest.fixture
def mock_urlopen():
    with patch('urllib.request.urlopen') as mock:
        yield mock

def test_read_url_best_effort_success(mock_urlopen):
    # Mock response
    mock_response = MagicMock()
    mock_response.read.return_value = b'{"path": "test.py", "content": "print(1)"}'
    mock_response.__enter__.return_value = mock_response
    mock_urlopen.return_value = mock_response

    url = "https://example.com/combined.json"
    content, encoding = utils.read_url_best_effort(url)

    assert content == '{"path": "test.py", "content": "print(1)"}'
    assert encoding == 'utf-8'

    # Verify User-Agent
    args, kwargs = mock_urlopen.call_args
    req = args[0]
    assert req.get_header('User-agent') == f'SourceCombine/{utils.__version__}'

def test_read_url_best_effort_failure(mock_urlopen):
    mock_urlopen.side_effect = Exception("Network error")

    url = "https://example.com/fail"
    content, encoding = utils.read_url_best_effort(url)

    assert content == ""
    assert encoding == 'utf-8'

def test_extract_from_remote_url(mock_urlopen, tmp_path, monkeypatch):
    # Setup mock response for URL
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps([
        {"path": "remote.py", "content": "remote content"}
    ]).encode('utf-8')
    mock_response.__enter__.return_value = mock_response
    mock_urlopen.return_value = mock_response

    output_dir = tmp_path / "out"

    # Mock sys.argv to simulate CLI call
    monkeypatch.setattr('sys.argv', [
        'sourcecombine.py',
        '--extract',
        'https://example.com/combined.json',
        '--output', str(output_dir)
    ])

    with pytest.raises(SystemExit) as excinfo:
        sourcecombine.main()

    assert excinfo.value.code == 0
    assert (output_dir / "remote.py").read_text() == "remote content"

def test_verify_from_remote_url(mock_urlopen, tmp_path, monkeypatch, capsys):
    # Setup file on disk
    file_on_disk = tmp_path / "verify.py"
    file_on_disk.write_text("on disk content")

    # Setup mock response for URL manifest
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps([
        {"path": "verify.py", "content": "on disk content"}
    ]).encode('utf-8')
    mock_response.__enter__.return_value = mock_response
    mock_urlopen.return_value = mock_response

    # Change CWD to tmp_path so relative paths work
    monkeypatch.chdir(tmp_path)

    monkeypatch.setattr('sys.argv', [
        'sourcecombine.py',
        '--verify',
        'https://example.com/manifest.json'
    ])

    with pytest.raises(SystemExit) as excinfo:
        sourcecombine.main()

    assert excinfo.value.code == 0
    out, err = capsys.readouterr()
    assert "[OK]" in out
    assert "verify.py" in out
