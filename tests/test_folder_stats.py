import io
import sys
import argparse
from pathlib import Path
import sourcecombine

def test_folder_stats_aggregation():
    top_files = [
        (100, 1000, "src/main.py"),
        (200, 2000, "src/utils.py"),
        (50, 500, "tests/test_main.py"),
        (10, 100, "README.md"),
    ]

    stats = sourcecombine._get_folder_stats(top_files)

    # Root folders are 'src' and 'tests'. 'README.md' parent is '.', which is skipped.
    assert 'src' in stats
    assert stats['src']['tokens'] == 300
    assert stats['src']['size'] == 3000
    assert stats['src']['lines'] == 0
    assert stats['src']['files'] == 2

    assert 'tests' in stats
    assert stats['tests']['tokens'] == 50
    assert stats['tests']['size'] == 500
    assert stats['tests']['lines'] == 0
    assert stats['tests']['files'] == 1

    assert '.' not in stats

def test_project_overview_includes_folders():
    stats = {
        'total_files': 4,
        'total_size_bytes': 3600,
        'total_tokens': 360,
        'total_lines': 100,
        'token_count_is_approx': False,
        'project_name': 'TestProj',
        'datetime': '2023-01-01 12:00:00',
        'top_files': [
            (100, 1000, "src/main.py"),
            (200, 2000, "src/utils.py"),
            (50, 500, "tests/test_main.py"),
            (10, 100, "README.md"),
        ]
    }

    # Test Text Output
    output_text = sourcecombine._generate_project_overview(stats, output_format='text')
    assert "Largest Folders (by tokens):" in output_text
    assert "src " in output_text
    assert "300 tokens" in output_text
    assert "2.93 KB" in output_text
    assert "•    2 files" in output_text

    # Test Markdown Output
    output_md = sourcecombine._generate_project_overview(stats, output_format='markdown')
    assert "## Largest Folders (by tokens)" in output_md
    assert "| Folder | Tokens | Size | Files | % |" in output_md
    assert "| `src` | 300 | 2.93 KB | 2 | 83.3% |" in output_md

def test_execution_summary_includes_folders():
    stats = {
        'total_files': 4,
        'total_size_bytes': 3600,
        'total_tokens': 360,
        'total_lines': 100,
        'token_count_is_approx': False,
        'project_name': 'TestProj',
        'datetime': '2023-01-01 12:00:00',
        'top_files': [
            (100, 1000, "src/main.py"),
            (200, 2000, "src/utils.py"),
            (50, 500, "tests/test_main.py"),
            (10, 100, "README.md"),
        ]
    }

    args = argparse.Namespace(dry_run=False, estimate_tokens=False, extract=False, list_files=False, tree=False)

    # Capture stderr
    old_stderr = sys.stderr
    sys.stderr = io.StringIO()
    try:
        sourcecombine._print_execution_summary(stats, args, pairing_enabled=False)
        output = sys.stderr.getvalue()
    finally:
        sys.stderr = old_stderr

    assert "Largest Folders (by tokens)" in output
    assert "TOKENS" in output
    assert "SIZE" in output
    assert "FOLDER" in output
    assert "src" in output
    assert "tests" in output

if __name__ == "__main__":
    test_folder_stats_aggregation()
    test_project_overview_includes_folders()
    test_execution_summary_includes_folders()
    print("All folder stats tests passed!")
