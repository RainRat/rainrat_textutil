import sys
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

# Adjust sys.path to include the project root
sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))

import sourcecombine

def test_summary_redesign_largest_files(monkeypatch, capsys):
    # Mock stats
    stats = {
        'total_files': 10,
        'total_size_bytes': 10000,
        'files_by_extension': {'.py': 5, '.md': 5},
        'total_tokens': 2500,
        'token_count_is_approx': False,
        'top_files': [
            (1000, 5000, "a/very/long/path/to/some/file/that/should/trigger/truncation/file.py"),
            (500, 2000, "short.py"),
        ]
    }

    # Mock args
    args = MagicMock()
    args.dry_run = False
    args.estimate_tokens = True
    args.list_files = False
    args.tree = False

    # Force NO_COLOR to avoid ANSI codes in test check
    monkeypatch.setenv("NO_COLOR", "1")

    # Force extract=False for this test to match "Combined"
    args.extract = False
    sourcecombine._print_execution_summary(stats, args, pairing_enabled=False)

    captured = capsys.readouterr()
    stderr = captured.err

    # Check for the new sections
    assert "TOKEN ESTIMATION COMPLETE: [Project]" in stderr
    assert "10 files" in stderr
    assert "Largest Files" in stderr
    assert "TOKENS" in stderr
    assert "%" in stderr
    assert "SIZE" in stderr
    assert "PATH" in stderr

    # Check for values
    assert "1,000" in stderr
    assert "40.0%" in stderr # (1000/2500)
    assert "4.88 KB" in stderr # (5000 bytes)
    assert "500" in stderr
    assert "20.0%" in stderr # (500/2500)
    assert "1.95 KB" in stderr # (2000 bytes)

    # Check for truncated path
    assert "a/very/long..." in stderr
    assert "ation/file.py" in stderr

def test_summary_printing(monkeypatch, capsys):
    # Mock stats
    stats = {
        'total_files': 123,
        'total_discovered': 123,
        'total_size_bytes': 1024 * 1024 * 1.5, # 1.5 MB
        'files_by_extension': {
            '.py': 10, '.txt': 5, '.md': 3, '.c': 1, '.h': 1,
            '.cpp': 1, '.hpp': 1, '.java': 1, '.js': 1, '.ts': 1,
            '.css': 1, '.html': 1, '.json': 1, '.xml': 1, '.yml': 1
        },
        'total_tokens': 5000,
        'token_count_is_approx': True,
        'excluded_folder_count': 2,
        'top_files': [
            (0, 1000, "file.txt")
        ]
    }

    # Mock args
    args = MagicMock()
    args.dry_run = False
    args.estimate_tokens = False
    args.list_files = False
    args.tree = False
    args.extract = False

    # Force NO_COLOR to avoid ANSI codes in test check
    monkeypatch.setenv("NO_COLOR", "1")

    sourcecombine._print_execution_summary(stats, args, pairing_enabled=False)

    captured = capsys.readouterr()
    stderr = captured.err

    assert "SUCCESS: [Project]" in stderr
    assert "Combined 123 files" in stderr
    assert "Total Found:" in stderr
    assert "123 files" in stderr
    assert "Skipped Folders:" in stderr
    assert "2 folders" in stderr
    assert "├── Included:" in stderr
    assert "Total Size:" in stderr
    assert "1.50 MB" in stderr
    assert "Largest Files" in stderr
    assert "SIZE" in stderr
    assert "%" in stderr
    assert "PATH" in stderr
    assert "File Types" in stderr
    assert "Skipped Folders:" in stderr
    assert "2" in stderr
    assert "Total Tokens:" in stderr
    assert "~5,000" in stderr

def test_summary_printing_dry_run(monkeypatch, capsys):
    stats = {
        'total_files': 0,
        'total_discovered': 0,
        'total_size_bytes': 0,
        'files_by_extension': {},
        'total_tokens': 0,
        'token_count_is_approx': False,
        'top_files': []
    }
    args = MagicMock()
    args.dry_run = True
    args.estimate_tokens = False
    args.list_files = False
    args.tree = False
    args.extract = False

    monkeypatch.setenv("NO_COLOR", "1")

    sourcecombine._print_execution_summary(stats, args, pairing_enabled=False)

    captured = capsys.readouterr()
    stderr = captured.err

    assert "NO FILES FOUND: [Project]" in stderr
    assert "Would combine 0 files" in stderr
    assert "Total Found:" in stderr
    assert "0 files" in stderr
    assert "├── Included:" not in stderr
    assert "Token Count" not in stderr

def test_output_truncated_warning(capsys):
    """Test summary shows truncation warning."""
    stats = {
        'total_files': 1,
        'total_size_bytes': 10,
        'files_by_extension': {'.txt': 1},
        'token_limit_reached': True,
        'total_tokens': 100,
        'max_total_tokens': 50,
        'top_files': []
    }

    args = MagicMock()
    args.list_files = False
    args.tree = False
    args.extract = False
    args.dry_run = False
    args.estimate_tokens = False

    with patch.dict(os.environ, {"NO_COLOR": "1"}):
        sourcecombine._print_execution_summary(stats, args, pairing_enabled=False)

    captured = capsys.readouterr()
    assert "WARNING: Output truncated due to token limit." in captured.err

def test_limit_bar_no_color(capsys):
    """Test limit bar with NO_COLOR=1."""
    stats = {
        'total_files': 1,
        'total_size_bytes': 10,
        'files_by_extension': {'.txt': 1},
        'total_tokens': 50,
        'max_total_tokens': 100,
        'top_files': []
    }

    args = MagicMock()
    args.list_files = False
    args.tree = False
    args.extract = False
    args.dry_run = False
    args.estimate_tokens = False

    with patch.dict(os.environ, {"NO_COLOR": "1"}):
        sourcecombine._print_execution_summary(stats, args, pairing_enabled=False)

    captured = capsys.readouterr()
    assert "Token Limit Usage:" in captured.err
    assert "[#####-----]" in captured.err

def test_summary_terminal_size_fallback(capsys):
    """Test terminal size fallback in extensions section."""
    stats = {
        'total_files': 1,
        'total_size_bytes': 10,
        'files_by_extension': {'.txt': 1},
        'top_files': []
    }

    args = MagicMock()
    args.list_files = False
    args.tree = False
    args.extract = False
    args.dry_run = False
    args.estimate_tokens = False

    with patch('sys.stderr.isatty', return_value=True):
        with patch.dict(os.environ, {"NO_COLOR": "1"}):
            with patch('shutil.get_terminal_size', side_effect=Exception("Terminal error")):
                sourcecombine._print_execution_summary(stats, args, pairing_enabled=False)

    captured = capsys.readouterr()
    stderr = captured.err
    assert "File Types" in stderr
    assert "EXTENSION" in stderr
    assert ".txt" in stderr

def test_summary_throughput_line(capsys):
    """Test that throughput is shown on its own line."""
    stats = {
        'total_files': 10,
        'total_discovered': 100,
        'total_size_bytes': 1000,
        'files_by_extension': {'.txt': 10},
        'top_files': []
    }

    args = MagicMock()
    args.list_files = False
    args.tree = False
    args.extract = False
    args.dry_run = False
    args.estimate_tokens = False

    with patch.dict(os.environ, {"NO_COLOR": "1"}):
        sourcecombine._print_execution_summary(stats, args, pairing_enabled=False, duration=2.0)

    captured = capsys.readouterr()
    assert "Time taken:" in captured.err
    assert "2.00 s" in captured.err
    assert "Throughput:" in captured.err
    assert "50.0 files/s" in captured.err

def test_file_types_redesign_sorting_and_others(monkeypatch, capsys):
    # Mock stats with 12 extensions.
    # .py should be top by weight even if .txt has more files.
    stats = {
        'total_files': 100,
        'total_discovered': 100,
        'total_included': 100,
        'total_size_bytes': 10000,
        'files_by_extension': {
            '.py': 10, '.txt': 50, '.md': 5, '.c1': 1, '.c2': 1,
            '.c3': 1, '.c4': 1, '.c5': 1, '.c6': 1, '.c7': 1,
            '.c8': 1, '.c9': 1
        },
        'tokens_by_extension': {
            '.py': 8000, '.txt': 1000, '.md': 500, '.c1': 50
        },
        'total_tokens': 10000,
        'token_count_is_approx': False,
        'top_files': []
    }

    args = MagicMock()
    args.dry_run = False
    args.estimate_tokens = True
    args.list_files = False
    args.tree = False
    args.extract = False

    monkeypatch.setenv("NO_COLOR", "1")

    sourcecombine._print_execution_summary(stats, args, pairing_enabled=False)

    captured = capsys.readouterr()
    stderr = captured.err

    # Check sorting: .py should be first despite having fewer files than .txt
    # Redesign uses a tabular format without colons
    ext_lines = [line for line in stderr.splitlines() if " [" in line and "]" in line and ("." in line or "(others)" in line) and "EXTENSION" not in line and "===" not in line]

    assert ".py" in ext_lines[0]
    assert ".txt" in ext_lines[1]

    # Check "others" aggregation (12 extensions total, top 10 shown, others aggregated)
    assert "(others)" in stderr

    # Check distribution bar
    # 80% -> 8 blocks -> [########--]
    assert "[########--]" in ext_lines[0]
    # 10% -> 1 block -> [#---------]
    assert "[#---------]" in ext_lines[1]

def test_jsonl_shortcut(monkeypatch):
    """Test that -J sets format to jsonl."""
    from unittest.mock import patch

    # We need to simulate the main() logic or at least the part that handles the shortcut
    # Actually, we can just test the parser and the subsequent logic in main()

    with patch('sys.argv', ['sourcecombine.py', '-J']):
        # We need to mock things so main doesn't actually run find_and_combine_files
        with patch('sourcecombine.find_and_combine_files') as mock_find:
            mock_find.return_value = {}
            with patch('sourcecombine._print_execution_summary'):
                with patch('sys.exit'):
                    try:
                        sourcecombine.main()
                    except SystemExit:
                        pass

                    # Check if format was set to jsonl in the config passed to find_and_combine_files
                    args, kwargs = mock_find.call_args
                    config = args[0]
                    assert config['output']['format'] == 'jsonl'

def test_skip_reasons_alignment(monkeypatch, capsys):
    stats = {
        'total_files': 5,
        'total_discovered': 10,
        'filter_reasons': {'excluded': 5},
        'total_size_bytes': 100,
        'files_by_extension': {'.py': 5},
        'total_tokens': 0,
        'top_files': []
    }

    args = MagicMock()
    args.dry_run = False
    args.estimate_tokens = False
    args.list_files = False
    args.tree = False
    args.extract = False

    monkeypatch.setenv("NO_COLOR", "1")

    sourcecombine._print_execution_summary(stats, args, pairing_enabled=False)

    captured = capsys.readouterr()
    stderr = captured.err

    # Check indentation and format of skip reason
    # "Excluded:" (9 chars) padded to label_width-8 (16) = 7 spaces
    # 5 is right-aligned in 12. Total 18 spaces between ':' and '5'.
    assert "└── Excluded:                  5 (100.0%)" in stderr


def test_summary_git_info(monkeypatch, capsys):
    # Mock stats with Git info
    stats = {
        'total_files': 1,
        'total_discovered': 1,
        'total_size_bytes': 100,
        'files_by_extension': {'.py': 1},
        'total_tokens': 10,
        'token_count_is_approx': False,
        'git_branch': 'main',
        'git_commit_short': 'a1b2c3d',
        'project_name': 'MyProj',
        'top_files': []
    }

    # Mock args
    args = MagicMock()
    args.dry_run = False
    args.estimate_tokens = False
    args.list_files = False
    args.tree = False
    args.extract = False

    # Force NO_COLOR to avoid ANSI codes in test check
    monkeypatch.setenv("NO_COLOR", "1")

    sourcecombine._print_execution_summary(stats, args, pairing_enabled=False)

    captured = capsys.readouterr()
    stderr = captured.err

    # Check for Git info in header
    assert "SUCCESS: [MyProj (main:a1b2c3d)]" in stderr
    assert "Combined 1 file" in stderr
