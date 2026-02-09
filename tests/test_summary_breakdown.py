from unittest.mock import MagicMock
import sourcecombine

def test_summary_filtering_breakdown(monkeypatch, capsys):
    stats = {
        'total_discovered': 100,
        'total_files': 60,
        'total_size_bytes': 1024,
        'files_by_extension': {'.py': 60},
        'filter_reasons': {
            'excluded': 20,
            'binary': 10,
            'too_large': 5,
            'too_small': 5
        },
        'excluded_folder_count': 0
    }

    args = MagicMock()
    args.dry_run = False
    args.estimate_tokens = False
    args.list_files = False
    args.tree = False

    monkeypatch.setenv("NO_COLOR", "1")

    sourcecombine._print_execution_summary(stats, args, pairing_enabled=False)

    captured = capsys.readouterr()
    stderr = captured.err

    assert f"{'Included:':<22}{60:12,}" in stderr
    assert f"{'Filtered:':<22}{40:12,}" in stderr
    assert f"- {'Excluded patterns':<18}{20:12,}" in stderr
    assert f"- {'Binary files':<18}{10:12,}" in stderr
    assert f"- {'Too large':<18}{5:12,}" in stderr
    assert f"- {'Too small':<18}{5:12,}" in stderr
    assert f"{'Total:':<22}{100:12,}" in stderr

def test_summary_budget_breakdown(monkeypatch, capsys):
    stats = {
        'total_discovered': 100,
        'total_files': 50,
        'total_size_bytes': 1024,
        'files_by_extension': {'.py': 50},
        'filter_reasons': {
            'budget_limit': 50
        },
        'budget_exceeded': True
    }

    args = MagicMock()
    args.dry_run = False
    args.estimate_tokens = False
    args.list_files = False
    args.tree = False

    monkeypatch.setenv("NO_COLOR", "1")

    sourcecombine._print_execution_summary(stats, args, pairing_enabled=False)

    captured = capsys.readouterr()
    stderr = captured.err

    assert "WARNING: Output truncated due to token budget." in stderr
    assert f"{'Filtered:':<22}{50:12,}" in stderr
    assert f"- {'Token budget limit':<18}{50:12,}" in stderr
