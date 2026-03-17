import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch


# Adjust sys.path to include the project root
sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))

import utils

def test_truncate_path_short_width():
    # Covers sourcecombine.py line 211
    from sourcecombine import _truncate_path
    # len("12345678901") = 11, max_width = 10
    # Should return "1234567..."
    assert _truncate_path("12345678901", 10) == "1234567..."
    # len("abc") = 3, max_width = 10
    assert _truncate_path("abc", 10) == "abc"

def test_render_global_template_stats_none():
    # Covers sourcecombine.py line 307
    from sourcecombine import _render_global_template
    assert _render_global_template("Template: {{FILE_COUNT}}", None) == "Template: {{FILE_COUNT}}"

def test_estimate_tokens_tiktoken_exception():
    # Covers utils.py lines 841-845
    with patch('utils.tiktoken') as mock_tiktoken:
        # Simulate tiktoken being installed but failing
        mock_tiktoken.get_encoding.side_effect = Exception("tiktoken failure")
        count, is_approx = utils.estimate_tokens("Some text")
        assert is_approx is True
        assert count == len("Some text") // 4

def test_process_paired_files_gaps(tmp_path):
    # Covers sourcecombine.py lines 849, 859-867
    from sourcecombine import _process_paired_files, FileProcessor

    root = tmp_path / "root"
    root.mkdir()
    f1 = root / "file1.cpp"
    f1.write_text("int main() { return 0; }", encoding="utf-8")

    paired_paths = {"file1": [f1]}
    processor = FileProcessor(config={}, output_opts={'max_size_placeholder': 'Too big: {{FILENAME}}'})
    stats = {
        'total_tokens': 0,
        'total_lines': 0,
        'total_files': 0,
        'total_size_bytes': 0,
        'files_by_extension': {},
        'top_files': [],
        'token_count_is_approx': False
    }

    # 1. Test estimate_tokens=True to cover line 849 (_DevNull)
    _process_paired_files(
        root_path=root,
        paired_paths=paired_paths,
        template="{{STEM}}.combined",
        source_exts=(".cpp",),
        header_exts=(".h",),
        out_folder=None,
        processor=processor,
        processing_bar=None,
        dry_run=False,
        estimate_tokens=True,
        stats=stats
    )
    assert stats['total_tokens'] > 0

    # 2. Test size_excluded to cover lines 859-867
    stats = {
        'total_tokens': 0,
        'total_lines': 0,
        'total_files': 0,
        'total_size_bytes': 0,
        'files_by_extension': {},
        'top_files': [],
        'token_count_is_approx': False
    }
    processing_bar = MagicMock()

    _process_paired_files(
        root_path=root,
        paired_paths=paired_paths,
        template="{{STEM}}.combined",
        source_exts=(".cpp",),
        header_exts=(".h",),
        out_folder=None,
        processor=processor,
        dry_run=False,
        estimate_tokens=False,
        size_excluded=[f1],
        stats=stats,
        processing_bar=processing_bar
    )

    assert len(stats['top_files']) == 1
    assert stats['total_tokens'] > 0
    processing_bar.update.assert_called_with(len(paired_paths["file1"]))
