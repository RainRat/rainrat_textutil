from sourcecombine import _generate_project_overview
import utils

def test_enhanced_overview_text():
    stats = {
        'total_files': 2,
        'total_size_bytes': 2048,
        'total_tokens': 500,
        'total_lines': 100,
        'git_branch': 'main',
        'git_commit_short': 'abc1234',
        'files_by_extension': {'.py': 1, '.md': 1},
        'tokens_by_extension': {'.py': 400, '.md': 100},
        'top_files': [
            (400, 1500, 'src/main.py'),
            (100, 548, 'README.md')
        ]
    }
    overview = _generate_project_overview(stats, output_format='text')

    assert "Project Overview:" in overview
    assert "Generated at:" in overview
    assert "Git Branch:   main" in overview
    assert "Git Commit:   abc1234" in overview
    assert "Files:        2" in overview
    assert "Total Size:   2.00 KB" in overview
    assert "Total Tokens: 500" in overview

    # Check Largest Files section
    assert "Largest Files (by tokens):" in overview
    assert "src/main.py" in overview
    assert "400 tokens" in overview
    assert "1.46 KB" in overview
    assert "( 80.0%)" in overview

    # Check File Types section with bars
    assert "File Types:" in overview
    assert ".py" in overview
    assert "1 files ( 50.0% •  80.0%) [########--]" in overview
    assert ".md" in overview
    assert "1 files ( 50.0% •  20.0%) [##--------]" in overview

def test_enhanced_overview_markdown():
    stats = {
        'total_files': 2,
        'total_size_bytes': 2048,
        'total_tokens': 500,
        'total_lines': 100,
        'git_branch': 'feat/cool-feature',
        'git_commit_short': 'def5678',
        'files_by_extension': {'.py': 1, '.md': 1},
        'tokens_by_extension': {'.py': 400, '.md': 100},
        'top_files': [
            (400, 1500, 'src/main.py'),
            (100, 548, 'README.md')
        ]
    }
    overview = _generate_project_overview(stats, output_format='markdown')

    assert "# Project Overview" in overview
    assert "**Generated at:**" in overview
    assert "**Git Branch:** feat/cool-feature" in overview
    assert "**Git Commit:** def5678" in overview
    assert "**Files:** 2" in overview

    # Check Largest Files table
    assert "## Largest Files (by tokens)" in overview
    assert "| File | Tokens | Size | % |" in overview
    assert "| `src/main.py` | 400 | 1.46 KB | 80.0% |" in overview

    # Check File Types table
    assert "## File Types" in overview
    assert "| Extension | Count | % Files | % Tokens |" in overview
    assert "| `.py` | 1 | 50.0% | 80.0% |" in overview
    assert "| `.md` | 1 | 50.0% | 20.0% |" in overview
