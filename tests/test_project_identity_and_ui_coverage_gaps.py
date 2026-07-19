import sys
import os
import json
import logging
import io
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

from utils import _format_author, get_project_identity
from sourcecombine import (
    FileProcessor,
    _generate_project_overview,
    _render_template,
    main
)

@pytest.fixture
def temp_cwd(tmp_path):
    original_cwd = os.getcwd()
    os.chdir(tmp_path)
    yield tmp_path
    os.chdir(original_cwd)

@pytest.fixture
def mock_stats():
    return {
        'total_files': 0,
        'total_discovered': 0,
        'total_size_bytes': 0,
        'files_by_language': {},
        'total_tokens': 0,
        'token_count_is_approx': False,
        'top_files': [],
        'filter_reasons': {}
    }

def test_format_author_empty():
    assert _format_author(None) == ""
    assert _format_author("") == ""

def test_format_author_unexpected_type():
    assert _format_author(12345) == "12345"

def test_csproj_project_author_extraction(tmp_path):
    csproj = tmp_path / "test.csproj"
    csproj.write_text('<Project><PropertyGroup><Authors>Jane Doe</Authors></PropertyGroup></Project>', encoding='utf-8')
    identity = get_project_identity(tmp_path)
    assert identity["project_author"] == "Jane Doe"

def test_podspec_project_author_extraction(tmp_path):
    podspec = tmp_path / "test.podspec"
    podspec.write_text("Pod::Spec.new do |s|\n  s.name = 'Test'\n  s.author = 'John Doe'\nend", encoding='utf-8')
    identity = get_project_identity(tmp_path)
    assert identity["project_author"] == "John Doe"

def test_pom_xml_project_author_extraction(tmp_path):
    pom = tmp_path / "pom.xml"
    pom.write_text('<project><developers><developer><name>Alice Dev</name></developer></developers></project>', encoding='utf-8')
    identity = get_project_identity(tmp_path)
    assert identity["project_author"] == "Alice Dev"

def test_gemspec_project_author_extraction(tmp_path):
    gemspec = tmp_path / "test.gemspec"
    gemspec.write_text("Gem::Specification.new do |s|\n  s.authors = ['Alice', 'Bob']\nend", encoding='utf-8')
    identity = get_project_identity(tmp_path)
    assert identity["project_author"] == "Alice, Bob"

def test_deno_json_single_author_extraction(tmp_path):
    deno = tmp_path / "deno.json"
    data = {"author": {"name": "Charlie", "email": "charlie@example.com"}}
    deno.write_text(json.dumps(data), encoding='utf-8')
    identity = get_project_identity(tmp_path)
    assert identity["project_author"] == "Charlie <charlie@example.com>"

def test_deno_json_multiple_authors_extraction(tmp_path):
    deno = tmp_path / "deno.json"
    data = {"authors": [{"name": "Charlie"}, {"name": "Dana"}]}
    deno.write_text(json.dumps(data), encoding='utf-8')
    identity = get_project_identity(tmp_path)
    assert identity["project_author"] == "Charlie, Dana"

def test_pubspec_yaml_author_extraction(tmp_path):
    pubspec = tmp_path / "pubspec.yaml"
    pubspec.write_text("name: app\nauthor: Jane Doe\n", encoding='utf-8')
    identity = get_project_identity(tmp_path)
    assert identity["project_author"] == "Jane Doe"

def test_empty_license_file_skipped(tmp_path):
    license_file = tmp_path / "LICENSE"
    license_file.write_text("  \n  ", encoding='utf-8')
    license_txt = tmp_path / "LICENSE.txt"
    license_txt.write_text("MIT License\nCopyright (c) 2025 Me", encoding='utf-8')
    identity = get_project_identity(tmp_path)
    assert identity["project_license"] == "MIT"

def test_write_max_size_placeholder_shebang_oserror(tmp_path):
    config = {"processing": {}}
    output_opts = {"max_size_placeholder": "Too big: {{FILENAME}} ({{LANG}})"}
    processor = FileProcessor(config, output_opts, dry_run=False)
    file_path = tmp_path / "script_no_ext"
    file_path.write_text("", encoding='utf-8')
    with patch("builtins.open", side_effect=OSError("Access Denied")):
        outfile = io.StringIO()
        tokens, approx, lines = processor.write_max_size_placeholder(
            file_path, tmp_path, outfile
        )
        assert "Too big" in outfile.getvalue()

def test_overview_text_format_all_fields_present():
    stats = {
        'total_files': 1,
        'total_size_bytes': 100,
        'total_tokens': 10,
        'total_lines': 5,
        'project_name': 'MyAwesomeProject',
        'project_version': '1.2.3',
        'project_author': 'Jane Doe',
        'project_license': 'MIT',
        'project_url': 'https://example.com',
        'manifest_source': 'package.json',
        'top_files': [(10, 100, 'file.txt', 'OK', 5, 'text')]
    }
    overview = _generate_project_overview(stats, output_format='text')
    assert "Project:      MyAwesomeProject" in overview
    assert "Version:      1.2.3" in overview
    assert "Author:       Jane Doe" in overview
    assert "License:      MIT" in overview
    assert "URL:          https://example.com" in overview
    assert "Manifest:     package.json" in overview

def test_overview_markdown_format_all_fields_present():
    stats = {
        'total_files': 1,
        'total_size_bytes': 100,
        'total_tokens': 10,
        'total_lines': 5,
        'project_name': 'MyAwesomeProject',
        'project_version': '1.2.3',
        'project_author': 'Jane Doe',
        'project_license': 'MIT',
        'project_url': 'https://example.com',
        'manifest_source': 'package.json',
        'top_files': [(10, 100, 'file.txt', 'OK', 5, 'text')]
    }
    overview = _generate_project_overview(stats, output_format='markdown')
    assert "- **Project:** MyAwesomeProject" in overview
    assert "- **Version:** 1.2.3" in overview
    assert "- **Author:** Jane Doe" in overview
    assert "- **License:** MIT" in overview
    assert "- **URL:** https://example.com" in overview
    assert "- **Manifest:** package.json" in overview

def test_overview_active_rules_single_line_comment_removal():
    stats = {
        'total_files': 1,
        'total_size_bytes': 100,
        'total_tokens': 0,
        'total_lines': 5,
    }
    processing_opts = {
        'remove_single_line_comments': True,
        'remove_all_c_style_comments': True
    }
    overview = _generate_project_overview(stats, output_format='text', processing_opts=processing_opts)
    assert "Single-line comment removal" in overview
    assert "C-style comment removal" in overview

def test_overview_by_lines_summary_text_and_markdown():
    stats = {
        'total_files': 10,
        'total_size_bytes': 1000,
        'total_tokens': 0,
        'total_lines': 100,
        'top_files': [
            (0, 500, 'file1.py', 'OK', 50, 'python'),
            (0, 500, 'file2.py', 'OK', 50, 'python')
        ]
    }
    overview_text = _generate_project_overview(stats, output_format='text')
    assert "Largest Files (by lines)" in overview_text
    assert "50 lines" in overview_text

    overview_md = _generate_project_overview(stats, output_format='markdown')
    assert "## Largest Files (by lines)" in overview_md
    assert "| File | Lines | Size | Language | % |" in overview_md

def test_overview_folders_by_lines_summary_text_and_markdown():
    stats = {
        'total_files': 10,
        'total_size_bytes': 1000,
        'total_tokens': 0,
        'total_lines': 100,
        'top_files': [
            (0, 500, 'src/file1.py', 'OK', 50, 'python'),
            (0, 500, 'lib/file2.py', 'OK', 50, 'python')
        ]
    }
    overview_text = _generate_project_overview(stats, output_format='text')
    assert "Largest Folders (by lines)" in overview_text
    assert "50 lines" in overview_text

    overview_md = _generate_project_overview(stats, output_format='markdown')
    assert "## Largest Folders (by lines)" in overview_md
    assert "| Folder | Lines | Size | Files | % |" in overview_md

def test_render_template_with_sha256():
    template = "Hash: {{HASH}}"
    rendered = _render_template(template, Path("file.txt"), sha256="my-fake-sha256")
    assert rendered == "Hash: my-fake-sha256"

def test_cli_ignore_file_none(temp_cwd, mock_stats):
    config_file = temp_cwd / "config.yml"
    config_file.write_text("search: {root_folders: ['.'], ignore_files: null}", encoding="utf-8")
    with patch('sourcecombine.find_and_combine_files', return_value=mock_stats) as mock_combine:
        with patch.object(sys, 'argv', ['sourcecombine.py', str(config_file), '--ignore-file', '.myignore']):
            main()
    args, _ = mock_combine.call_args
    config = args[0]
    assert isinstance(config['search']['ignore_files'], list)
    assert '.myignore' in config['search']['ignore_files']

def test_cli_exclude_extensions_none(temp_cwd, mock_stats):
    config_file = temp_cwd / "config.yml"
    config_file.write_text("search: {root_folders: ['.'], exclude_extensions: null}", encoding="utf-8")
    with patch('sourcecombine.find_and_combine_files', return_value=mock_stats) as mock_combine:
        with patch.object(sys, 'argv', ['sourcecombine.py', str(config_file), '--exclude-extension', '.foo']):
            main()
    args, _ = mock_combine.call_args
    config = args[0]
    assert isinstance(config['search']['exclude_extensions'], list)
    assert '.foo' in config['search']['exclude_extensions']
