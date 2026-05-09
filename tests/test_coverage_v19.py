import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
import sourcecombine

def test_construct_git_web_url_unknown_provider():
    # Unknown provider with relative path should return None
    url = sourcecombine._construct_git_web_url("https://unknown.com/repo.git", "main", "file.py")
    assert url is None

def test_render_template_file_url_value_error():
    # Test ValueError in _render_template during {{FILE_URL}} generation
    # This happens if Path.relative_to fails (e.g., file outside repo)
    git_info = {
        "git_remote_url": "https://github.com/User/Repo.git",
        "git_commit": "abc1234",
        "git_repo_root": "/app/repo"
    }
    template = "{{FILE_URL}}"
    file_path = "/other/path/file.py"

    # We need to ensure resolve() returns different things so relative_to fails
    # Or just mock relative_to directly on the Path instance if possible
    # But Path objects are immutable and hard to mock directly.
    # We can mock Path.relative_to globally.
    with patch("pathlib.Path.relative_to", side_effect=ValueError("Outside repo")):
        rendered = sourcecombine._render_template(
            template, Path("file.py"), git_info=git_info, file_path=file_path
        )

    assert rendered == ""

def test_render_template_file_url_os_error():
    # Test OSError in _render_template during {{FILE_URL}} generation
    # This happens if Path.resolve() fails
    git_info = {
        "git_remote_url": "https://github.com/User/Repo.git",
        "git_commit": "abc1234",
        "git_repo_root": "/app/repo"
    }
    template = "{{FILE_URL}}"
    file_path = "/app/repo/file.py"

    with patch("pathlib.Path.resolve", side_effect=OSError("Mocked OS Error")):
        rendered = sourcecombine._render_template(
            template, Path("file.py"), git_info=git_info, file_path=file_path
        )

    assert rendered == ""
