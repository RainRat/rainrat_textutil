from sourcecombine import _generate_project_overview

def test_overview_largest_files_by_size():
    stats = {
        'total_files': 1,
        'total_size_bytes': 100,
        'total_tokens': 0,
        'total_lines': 5,
        'top_files': [(0, 100, 'file.txt')]
    }
    overview = _generate_project_overview(stats, output_format='text')
    assert "Largest Files (by size):" in overview
    assert "file.txt" in overview

def test_overview_ascii_bar_minimum_fill():
    stats = {
        'total_files': 10,
        'total_size_bytes': 1000,
        'total_tokens': 0,
        'total_lines': 100,
        'files_by_language': {'.txt': 1, '.other': 9},
        'size_by_language': {'.txt': 20, '.other': 980}
    }
    overview = _generate_project_overview(stats, output_format='text')
    assert "[#---------]" in overview
