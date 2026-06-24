import json
import os
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import sourcecombine
import utils

@pytest.fixture
def mock_git_info(monkeypatch):
    """Mock subprocess.run to return controlled Git information."""
    def mock_run(args, **kwargs):
        cmd = " ".join(args) if isinstance(args, list) else args

        stdout = ""
        if 'rev-parse --show-toplevel' in cmd:
            stdout = os.getcwd()
        elif 'rev-parse --abbrev-ref HEAD' in cmd:
            stdout = "main"
        elif 'log -1 --format=%H%n%an%n%ai' in cmd:
            stdout = "hash\nauthor\n2023-01-01"
        elif 'describe --tags --abbrev=0' in cmd:
            stdout = "v1.2.3"
        elif 'remote get-url origin' in cmd:
            stdout = "https://github.com/user/repo.git"
        elif 'status --porcelain' in cmd:
            stdout = ""

        return MagicMock(stdout=stdout, returncode=0)

    monkeypatch.setattr(subprocess, "run", mock_run)

def test_get_git_info_with_tag(mock_git_info):
    """Verify that _get_git_info correctly retrieves the Git tag."""
    info = sourcecombine._get_git_info(".")
    assert info['git_tag'] == "v1.2.3"

def test_dynamic_output_path_resolution(mock_git_info, tmp_path, monkeypatch):
    """Verify that find_and_combine_files resolves placeholders in output_path."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "test.txt").write_text("content")

    import copy
    config = copy.deepcopy(utils.DEFAULT_CONFIG)
    config['search']['root_folders'] = [str(tmp_path)]

    output_template = "output_{{GIT_BRANCH}}.txt"
    # stats will have git_branch='main'

    stats = sourcecombine.find_and_combine_files(
        config,
        output_path=output_template,
    )

    expected_path = tmp_path / "output_main.txt"
    assert stats['resolved_output_path'] == "output_main.txt"
    assert expected_path.exists()
    assert "content" in expected_path.read_text()

def test_json_summary_path_resolution(mock_git_info, tmp_path, monkeypatch):
    """Verify that main() resolves placeholders in the json-summary path."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "test.txt").write_text("content")

    # Mock sys.argv
    test_args = [
        "sourcecombine.py",
        str(tmp_path),
        "--output", "out.txt",
        "--json-summary", "summary_{{PROJECT_NAME}}.json"
    ]

    with patch("sys.argv", test_args):
        # We need to mock sys.exit to prevent the test from exiting
        with patch("sys.exit") as mock_exit:
            sourcecombine.main()

    # Project name defaults to the folder name in get_project_identity
    project_name = tmp_path.name
    expected_summary = tmp_path / f"summary_{project_name}.json"

    assert expected_summary.exists()
    with open(expected_summary) as f:
        data = json.load(f)
        assert data['total_files'] == 1

def test_git_tag_placeholder_in_template(mock_git_info, tmp_path, monkeypatch):
    """Verify that {{GIT_TAG}} is correctly resolved in templates."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "test.txt").write_text("content")

    import copy
    config = copy.deepcopy(utils.DEFAULT_CONFIG)
    config['search']['root_folders'] = [str(tmp_path)]
    config['output']['header_template'] = "Tag: {{GIT_TAG}}\n"

    output_path = tmp_path / "out.txt"
    sourcecombine.find_and_combine_files(
        config,
        output_path=str(output_path),
    )

    content = output_path.read_text()
    assert "Tag: v1.2.3" in content
