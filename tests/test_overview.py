import sys
import os
from pathlib import Path

# Adjust sys.path to include the project root
sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))

import sourcecombine

def test_overview_generation_text():
    stats = {
        'total_files': 2,
        'total_size_bytes': 1024,
        'total_tokens': 250,
        'total_lines': 50,
        'files_by_language': {'python': 1, 'markdown': 1}
    }
    overview = sourcecombine._generate_project_overview(stats, output_format='text')
    assert "Project Overview:" in overview
    assert "Files:        2" in overview
    assert "Total Size:   1.00 KB" in overview
    assert "python" in overview
    assert "markdown" in overview

def test_overview_generation_markdown():
    stats = {
        'total_files': 2,
        'total_size_bytes': 1024,
        'total_tokens': 250,
        'total_lines': 50,
        'files_by_language': {'python': 1, 'markdown': 1}
    }
    overview = sourcecombine._generate_project_overview(stats, output_format='markdown')
    assert "# Project Overview" in overview
    assert "## Statistics" in overview
    assert "| Language | Count |" in overview
    assert "`python`" in overview
    assert "`markdown`" in overview

def test_overview_no_stats():
    assert sourcecombine._generate_project_overview(None) == ""
    assert sourcecombine._generate_project_overview({}) == ""
