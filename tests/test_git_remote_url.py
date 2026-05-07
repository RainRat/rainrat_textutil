import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
import sourcecombine

def test_construct_git_web_url():
    # GitHub HTTPS
    url = sourcecombine._construct_git_web_url("https://github.com/User/Repo.git", "main")
    assert url == "https://github.com/User/Repo"

    url = sourcecombine._construct_git_web_url("https://github.com/User/Repo.git", "main", "src/main.py")
    assert url == "https://github.com/User/Repo/blob/main/src/main.py"

    # GitHub SSH
    url = sourcecombine._construct_git_web_url("git@github.com:User/Repo.git", "abc1234")
    assert url == "https://github.com/User/Repo"

    url = sourcecombine._construct_git_web_url("git@github.com:User/Repo.git", "abc1234", "src/main.py")
    assert url == "https://github.com/User/Repo/blob/abc1234/src/main.py"

    # GitLab HTTPS
    url = sourcecombine._construct_git_web_url("https://gitlab.com/User/Repo.git", "main", "src/main.py")
    assert url == "https://gitlab.com/User/Repo/-/blob/main/src/main.py"

    # Bitbucket HTTPS
    url = sourcecombine._construct_git_web_url("https://bitbucket.org/User/Repo.git", "main", "src/main.py")
    assert url == "https://bitbucket.org/User/Repo/src/main/src/main.py"

def test_get_git_info_with_remote(tmp_path):
    # Mock subprocess.run to avoid needing a real git repo
    def mock_run(args, **kwargs):
        mock = MagicMock()
        mock.returncode = 0
        if "--show-toplevel" in args:
            mock.stdout = str(tmp_path)
        elif "--abbrev-ref" in args:
            mock.stdout = "main"
        elif "rev-parse" in args and "HEAD" in args:
            mock.stdout = "abc1234567890"
        elif "remote" in args and "get-url" in args:
            mock.stdout = "https://github.com/User/Repo.git"
        elif "status" in args:
            mock.stdout = ""
        else:
            mock.stdout = ""
        return mock

    with patch("subprocess.run", side_effect=mock_run):
        info = sourcecombine._get_git_info(str(tmp_path))

    assert info["git_remote_url"] == "https://github.com/User/Repo.git"
    assert info["git_repo_root"] == tmp_path.as_posix()
    assert info["git_branch"] == "main"
    assert info["git_commit"] == "abc1234567890"

def test_render_placeholders():
    git_info = {
        "git_remote_url": "https://github.com/User/Repo.git",
        "git_commit": "abc1234",
        "git_repo_root": "/app/repo",
        "git_branch": "main"
    }

    # Global template
    template = "Project: {{PROJECT_URL}}, Remote: {{GIT_REMOTE_URL}}"
    rendered = sourcecombine._render_global_template(template, git_info)
    assert "Project: https://github.com/User/Repo" in rendered
    assert "Remote: https://github.com/User/Repo.git" in rendered

    # File template
    # Mocking file_path as if it's /app/repo/src/main.py
    file_path = "/app/repo/src/main.py"
    template = "File: {{FILE_URL}}, Remote: {{GIT_REMOTE_URL}}"

    # We need to be careful with Path resolution in tests
    with patch("pathlib.Path.resolve", return_value=Path(file_path)):
        with patch("pathlib.Path.relative_to", return_value=Path("src/main.py")):
            rendered = sourcecombine._render_template(
                template, Path("src/main.py"), git_info=git_info, file_path=file_path
            )

    assert "File: https://github.com/User/Repo/blob/abc1234/src/main.py" in rendered
    assert "Remote: https://github.com/User/Repo.git" in rendered
