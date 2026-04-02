import pytest
from pathlib import Path
from sourcecombine import find_and_combine_files, extract_files
import utils

@pytest.fixture
def temp_project(tmp_path):
    """Create a temporary project with files of different sizes and line counts."""
    # 1 line, ~3 tokens
    (tmp_path / "small.txt").write_text("Hello world one.", encoding="utf-8")

    # 5 lines, ~15 tokens
    (tmp_path / "medium.txt").write_text("Line 1\nLine 2\nLine 3\nLine 4\nLine 5\n", encoding="utf-8")

    # 10 lines, ~100 tokens
    long_content = "\n".join([f"This is line {i} with some extra text to increase token count significantly." for i in range(10)])
    (tmp_path / "large.txt").write_text(long_content, encoding="utf-8")

    return tmp_path

def test_min_tokens_filter(temp_project):
    config = utils.DEFAULT_CONFIG.copy()
    config['search'] = {'root_folders': [str(temp_project)], 'recursive': False}
    config['filters'] = {'min_tokens': 50}

    stats = find_and_combine_files(config, output_path=None, dry_run=True)

    # Should only include large.txt
    assert stats['total_files'] == 1
    assert any("large.txt" in f[2] for f in stats['top_files'])
    assert stats['filter_reasons'].get('too_few_tokens') == 2

def test_max_tokens_filter(temp_project):
    config = utils.DEFAULT_CONFIG.copy()
    config['search'] = {'root_folders': [str(temp_project)], 'recursive': False}
    config['filters'] = {'max_tokens': 20}

    stats = find_and_combine_files(config, output_path=None, dry_run=True)

    # Should include small.txt and medium.txt
    assert stats['total_files'] == 2
    assert any("small.txt" in f[2] for f in stats['top_files'])
    assert any("medium.txt" in f[2] for f in stats['top_files'])
    assert stats['filter_reasons'].get('too_many_tokens') == 1

def test_min_lines_filter(temp_project):
    config = utils.DEFAULT_CONFIG.copy()
    config['search'] = {'root_folders': [str(temp_project)], 'recursive': False}
    config['filters'] = {'min_lines': 5}

    stats = find_and_combine_files(config, output_path=None, dry_run=True)

    # Should include medium.txt (5 lines) and large.txt (10 lines)
    assert stats['total_files'] == 2
    assert any("medium.txt" in f[2] for f in stats['top_files'])
    assert any("large.txt" in f[2] for f in stats['top_files'])
    assert stats['filter_reasons'].get('too_few_lines') == 1

def test_max_lines_filter(temp_project):
    config = utils.DEFAULT_CONFIG.copy()
    config['search'] = {'root_folders': [str(temp_project)], 'recursive': False}
    config['filters'] = {'max_lines': 5}

    stats = find_and_combine_files(config, output_path=None, dry_run=True)

    # Should include small.txt and medium.txt
    assert stats['total_files'] == 2
    assert any("small.txt" in f[2] for f in stats['top_files'])
    assert any("medium.txt" in f[2] for f in stats['top_files'])
    assert stats['filter_reasons'].get('too_many_lines') == 1

def test_extraction_with_metric_filters(temp_project, tmp_path):
    # Combine all files into JSON
    config = utils.DEFAULT_CONFIG.copy()
    config['search'] = {'root_folders': [str(temp_project)], 'recursive': False}
    combined_json = tmp_path / "combined.json"
    find_and_combine_files(config, output_path=str(combined_json), output_format='json')

    # Extract with max_tokens filter
    extract_config = utils.DEFAULT_CONFIG.copy()
    extract_config['filters'] = {'max_tokens': 20}

    output_dir = tmp_path / "extracted"
    output_dir.mkdir()

    sources = [(str(combined_json), combined_json.read_text(encoding="utf-8"))]
    stats = extract_files(sources, str(output_dir), config=extract_config)

    # Should only extract 2 files
    assert stats['total_files'] == 2
    assert (output_dir / "small.txt").exists()
    assert (output_dir / "medium.txt").exists()
    assert not (output_dir / "large.txt").exists()
    assert stats['filter_reasons'].get('too_many_tokens') == 1

def test_main_cli_injection(monkeypatch, temp_project):
    import sourcecombine
    import sys

    # Mock sys.argv
    args = [
        "sourcecombine.py", str(temp_project),
        "--min-tokens", "10",
        "--max-file-tokens", "100",
        "--min-lines", "2",
        "--max-file-lines", "20",
        "--dry-run"
    ]
    monkeypatch.setattr(sys, "argv", args)

    # We want to capture the config passed to find_and_combine_files
    captured_config = {}
    def mock_combine(config, *args, **kwargs):
        captured_config.update(config)
        return {
            'total_files': 0,
            'total_discovered': 0,
            'total_size_bytes': 0,
            'total_tokens': 0,
            'total_lines': 0,
            'files_by_extension': {},
            'top_files': [],
            'filter_reasons': {}
        }

    monkeypatch.setattr(sourcecombine, "find_and_combine_files", mock_combine)

    # Run main, ignoring exit
    try:
        sourcecombine.main()
    except SystemExit:
        pass

    filters = captured_config.get('filters', {})
    assert filters.get('min_tokens') == 10
    assert filters.get('max_tokens') == 100
    assert filters.get('min_lines') == 2
    assert filters.get('max_lines') == 20
