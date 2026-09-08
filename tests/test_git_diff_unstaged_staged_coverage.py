import sys
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import sourcecombine


def test_collect_git_diff_files_staged_only_without_diff_ref(tmp_path):
    f1 = tmp_path / "staged.txt"
    f1.write_text("staged content")

    def mock_run(args, cwd, capture_output, text, check):
        mock_res = MagicMock()
        if "--cached" in args and "HEAD~1" not in args:
            mock_res.stdout = "staged.txt\ndeleted.txt\n"
        else:
            mock_res.stdout = ""
        return mock_res

    progress_mock = MagicMock()
    with patch("subprocess.run", side_effect=mock_run) as mock_sub:
        files, root, excluded = sourcecombine.collect_git_diff_files(
            tmp_path, diff_ref=None, progress=progress_mock, staged_only=True
        )

    assert files == [f1]
    assert root == tmp_path
    assert excluded == 0
    assert progress_mock.update.called


def test_collect_git_diff_files_staged_only_with_diff_ref(tmp_path):
    f1 = tmp_path / "staged.txt"
    f1.write_text("staged content")

    executed_cmds = []

    def mock_run(args, cwd, capture_output, text, check):
        executed_cmds.append(args)
        mock_res = MagicMock()
        if "main" in args:
            mock_res.stdout = "staged.txt\n"
        else:
            mock_res.stdout = ""
        return mock_res

    with patch("subprocess.run", side_effect=mock_run):
        files, root, excluded = sourcecombine.collect_git_diff_files(
            tmp_path, diff_ref="main", staged_only=True
        )

    assert files == [f1]
    assert any("main" in cmd for cmd in executed_cmds)


def test_collect_git_diff_files_unstaged_only(tmp_path):
    f1 = tmp_path / "unstaged.txt"
    f1.write_text("unstaged content")
    f2 = tmp_path / "untracked.txt"
    f2.write_text("untracked content")

    executed_cmds = []

    def mock_run(args, cwd, capture_output, text, check):
        executed_cmds.append(args)
        mock_res = MagicMock()
        if "ls-files" in args:
            mock_res.stdout = "untracked.txt\n"
        else:
            mock_res.stdout = "unstaged.txt\n"
        return mock_res

    with patch("subprocess.run", side_effect=mock_run):
        files, root, excluded = sourcecombine.collect_git_diff_files(
            tmp_path, diff_ref=None, unstaged_only=True
        )

    assert sorted(files) == sorted([f1, f2])
    assert len(executed_cmds) == 2


def test_collect_git_diff_files_default_with_custom_diff_ref(tmp_path):
    f1 = tmp_path / "changed.txt"
    f1.write_text("changed content")

    executed_cmds = []

    def mock_run(args, cwd, capture_output, text, check):
        executed_cmds.append(args)
        mock_res = MagicMock()
        if "v1.0" in args:
            mock_res.stdout = "changed.txt\n"
        else:
            mock_res.stdout = ""
        return mock_res

    with patch("subprocess.run", side_effect=mock_run):
        files, root, excluded = sourcecombine.collect_git_diff_files(
            tmp_path, diff_ref="v1.0"
        )

    assert files == [f1]
    assert any("v1.0" in cmd for cmd in executed_cmds)
