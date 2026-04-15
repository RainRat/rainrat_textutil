from unittest.mock import MagicMock, patch
import argparse
import sys
from pathlib import Path
import pytest
import sourcecombine
import utils

def test_collect_git_diff_files_staged_with_ref(tmp_path):
    """Test collect_git_diff_files with staged_only=True and a diff_ref."""
    root = tmp_path
    diff_ref = "HEAD~1"

    # Mocking subprocess for 'git diff --name-only --cached --relative HEAD~1'
    mock_diff = MagicMock()
    mock_diff.stdout = "staged_ref.py\n"

    (root / "staged_ref.py").touch()

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = mock_diff

        file_paths, root_path, excluded = sourcecombine.collect_git_diff_files(
            root, staged_only=True, diff_ref=diff_ref
        )

        assert len(file_paths) == 1
        assert file_paths[0].name == "staged_ref.py"
        mock_run.assert_called_with(
            ['git', 'diff', '--name-only', '--cached', '--relative', 'HEAD~1'],
            cwd=root, capture_output=True, text=True, check=True
        )

def test_main_git_staged_unstaged_injection(monkeypatch):
    """Test that --staged and --unstaged flags are correctly injected into config."""

    config_captured = None

    def mock_find_and_combine(config, output_path, **kwargs):
        nonlocal config_captured
        config_captured = config
        return {}

    # Mock find_and_combine_files to capture the config
    monkeypatch.setattr(sourcecombine, "find_and_combine_files", mock_find_and_combine)
    # Mock sys.exit to prevent test from exiting
    monkeypatch.setattr(sys, "exit", lambda x: None)

    # Test --staged
    monkeypatch.setattr(sys, "argv", ["sourcecombine.py", "--staged"])
    sourcecombine.main()
    assert config_captured['search']['git_staged'] is True
    assert config_captured['search']['use_git_diff'] is True

    # Test --unstaged
    monkeypatch.setattr(sys, "argv", ["sourcecombine.py", "--unstaged"])
    sourcecombine.main()
    assert config_captured['search']['git_unstaged'] is True
    assert config_captured['search']['use_git_diff'] is True

def test_validate_search_section_invalid_git_bools():
    """Test that utils._validate_search_section raises InvalidConfigError for non-boolean git_staged/unstaged."""

    # Invalid git_staged
    invalid_search_staged = {'search': {'git_staged': 'not-a-bool'}}
    with pytest.raises(utils.InvalidConfigError, match="search.git_staged must be true or false"):
        utils._validate_search_section(invalid_search_staged)

    # Invalid git_unstaged
    invalid_search_unstaged = {'search': {'git_unstaged': 'not-a-bool'}}
    with pytest.raises(utils.InvalidConfigError, match="search.git_unstaged must be true or false"):
        utils._validate_search_section(invalid_search_unstaged)
