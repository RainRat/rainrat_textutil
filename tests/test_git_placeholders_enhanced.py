from unittest.mock import MagicMock, patch
from pathlib import Path
import sourcecombine
import utils

def test_git_placeholders_enhanced(tmp_path):
    """Test that {{FILE_DIFF}} and {{GIT_LOG}} are correctly replaced in templates."""
    root = tmp_path
    (root / "file1.py").write_text("print('hello')", encoding='utf-8')

    # Mock Git info
    git_diff_text = """diff --git a/file1.py b/file1.py
index e69de29..d00491f 100644
--- a/file1.py
+++ b/file1.py
@@ -0,0 +1 @@
+print('hello')
"""
    git_log_text = "feat: initial commit"

    mock_git_info = {
        'git_branch': 'main',
        'git_commit': 'abcdef1234567890',
        'git_commit_short': 'abcdef1',
        'git_log': git_log_text,
        'git_diff': git_diff_text,
        'file_diffs': {
            'file1.py': git_diff_text
        }
    }

    # Configure with templates using the new placeholders
    config = utils.DEFAULT_CONFIG.copy()
    config['search'] = config['search'].copy()
    config['search']['root_folders'] = [str(root)]

    config['output'] = config['output'].copy()
    config['output']['header_template'] = "Header: {{FILENAME}} | Log: {{GIT_LOG}} | FileDiff:\n{{FILE_DIFF}}\n"
    config['output']['global_header_template'] = "Global Log: {{GIT_LOG}}"
    config['output']['file'] = str(tmp_path / "output.txt")

    with patch("sourcecombine._get_git_info", return_value=mock_git_info):
        sourcecombine.find_and_combine_files(config, str(tmp_path / "output.txt"))

    output_content = (tmp_path / "output.txt").read_text(encoding='utf-8')

    assert "Global Log: feat: initial commit" in output_content
    assert "Header: file1.py | Log: feat: initial commit | FileDiff:" in output_content
    assert "print('hello')" in output_content
    assert "diff --git a/file1.py b/file1.py" in output_content

def test_parse_git_diff_by_file():
    """Test that _parse_git_diff_by_file splits a multi-file diff correctly."""
    diff_text = """diff --git a/file1.py b/file1.py
index e69de29..d00491f 100644
--- a/file1.py
+++ b/file1.py
@@ -0,0 +1 @@
+print('hello')
diff --git a/dir/file2.txt b/dir/file2.txt
index e69de29..d00491f 100644
--- a/dir/file2.txt
+++ b/dir/file2.txt
@@ -0,0 +1 @@
+world
"""
    file_diffs = sourcecombine._parse_git_diff_by_file(diff_text)

    assert len(file_diffs) == 2
    assert "file1.py" in file_diffs
    assert "dir/file2.txt" in file_diffs
    assert "diff --git a/file1.py b/file1.py" in file_diffs["file1.py"]
    assert "diff --git a/dir/file2.txt b/dir/file2.txt" in file_diffs["dir/file2.txt"]
    assert "print('hello')" in file_diffs["file1.py"]
    assert "world" in file_diffs["dir/file2.txt"]
