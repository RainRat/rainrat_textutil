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


def test_overview_text_format_project_details_gaps():
    stats = {
        'project_name': 'MyProj',
        'project_version': '1.0.0',
        'project_author': 'Author Name',
        'project_license': 'MIT',
        'project_url': 'https://example.com',
        'manifest_source': 'package.json',
        'total_files': 1,
        'total_size_bytes': 100,
        'total_tokens': 0,
        'total_lines': 5,
    }
    overview = _generate_project_overview(stats, output_format='text')
    assert "Project:      MyProj" in overview
    assert "Version:      1.0.0" in overview
    assert "Author:       Author Name" in overview
    assert "License:      MIT" in overview
    assert "URL:          https://example.com" in overview
    assert "Manifest:     package.json" in overview


def test_overview_markdown_folder_has_lines_gaps():
    stats = {
        'total_files': 2,
        'total_size_bytes': 300,
        'total_tokens': 30,
        'total_lines': 15,
        'top_files': [
            (10, 100, "src/main.py", "ok", 5),
            (20, 200, "tests/test.py", "ok", 10)
        ]
    }
    overview = _generate_project_overview(stats, output_format='markdown')
    assert "| Folder | Tokens | Lines | Size | Files | % |" in overview


def test_overview_processing_opts_removal_rules():
    stats = {
        'total_files': 1,
        'total_size_bytes': 100,
        'total_tokens': 50,
        'total_lines': 5,
    }
    opts_remove_comments = {
        'remove_comments': True
    }
    overview = _generate_project_overview(stats, output_format='text', processing_opts=opts_remove_comments)
    assert "Comment removal" in overview

    opts_remove_single = {
        'remove_single_line_comments': True
    }
    overview2 = _generate_project_overview(stats, output_format='text', processing_opts=opts_remove_single)
    assert "Single-line comment removal" in overview2


def test_render_template_with_explicit_sha256_hash():
    from pathlib import Path
    from sourcecombine import _render_template
    template = "Hash: {{HASH}}"
    relative_path = Path("test.py")
    result = _render_template(template, relative_path, sha256="explicit_sha256_value")
    assert "explicit_sha256_value" in result


def test_write_max_size_placeholder_oserror_handling(tmp_path):
    import io
    from sourcecombine import FileProcessor
    config = {"processing": {}}
    output_opts = {"max_size_placeholder": "Too big: {{FILENAME}} ({{LANG}})"}
    processor = FileProcessor(config, output_opts, dry_run=False)
    dir_path = tmp_path / "subdir_not_file"
    dir_path.mkdir()
    outfile = io.StringIO()
    tokens, approx, lines = processor.write_max_size_placeholder(dir_path, tmp_path, outfile)
    assert tokens > 0
    assert approx is False
