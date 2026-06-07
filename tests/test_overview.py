from sourcecombine import _generate_project_overview, find_and_combine_files
import utils

def test_overview_generation_text():
    stats = {
        'total_files': 2,
        'total_size_bytes': 1024,
        'total_tokens': 250,
        'total_lines': 50,
        'files_by_extension': {'.py': 1, '.md': 1}
    }
    overview = _generate_project_overview(stats, output_format='text')
    assert "Project Overview:" in overview
    assert "Files:        2" in overview
    assert "Total Size:   1.00 KB" in overview
    assert ".py" in overview
    assert ".md" in overview

def test_overview_generation_markdown():
    stats = {
        'total_files': 2,
        'total_size_bytes': 1024,
        'total_tokens': 250,
        'total_lines': 50,
        'files_by_extension': {'.py': 1, '.md': 1}
    }
    overview = _generate_project_overview(stats, output_format='markdown')
    assert "# Project Overview" in overview
    assert "## Statistics" in overview
    assert "| Extension | Count |" in overview
    assert "| `.py` | 1 |" in overview

def test_overview_truncation_notices():
    stats = {
        'total_files': 1,
        'total_size_bytes': 100,
        'total_tokens': 20,
        'total_lines': 5,
        'token_limit_reached': True,
        'size_limit_reached': True
    }
    overview = _generate_project_overview(stats, output_format='text')
    assert "WARNING: Output shortened due to: token limit, size limit" in overview

def test_overview_applied_processing():
    stats = {
        'total_files': 1,
        'total_size_bytes': 100,
        'total_tokens': 20,
        'total_lines': 5
    }
    processing_opts = {
        'compact_whitespace': True,
        'max_lines': 10
    }
    overview = _generate_project_overview(stats, output_format='text', processing_opts=processing_opts)
    assert "Applied Processing:" in overview
    assert "Whitespace compaction" in overview
    assert "Shortened to 10 lines per file" in overview

def test_find_and_combine_with_overview(tmp_path):
    # Create dummy files
    (tmp_path / "file1.py").write_text("print('hello')", encoding='utf-8')
    (tmp_path / "file2.txt").write_text("just some text", encoding='utf-8')

    output_file = tmp_path / "combined.txt"

    config = utils.DEFAULT_CONFIG.copy()
    config['search'] = {'root_folders': [str(tmp_path)]}
    config['output'] = {
        'project_overview': True,
        'format': 'text',
        'file': str(output_file)
    }

    find_and_combine_files(config, str(output_file))

    content = output_file.read_text(encoding='utf-8')
    assert "Project Overview:" in content
    assert "Files:        2" in content
    assert ".py" in content
    assert ".txt" in content
    assert "--- file1.py ---" in content
