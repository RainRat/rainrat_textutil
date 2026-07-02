import os
import json
from pathlib import Path
import pytest
from utils import _parse_json_manifest, get_project_identity, DEFAULT_CONFIG
from sourcecombine import find_and_combine_files, _generate_project_overview

def test_parse_json_manifest_repository_string(tmp_path):
    manifest = tmp_path / "package.json"
    manifest.write_text(json.dumps({
        "name": "test-repo",
        "repository": "https://github.com/user/repo"
    }), encoding='utf-8')

    identity = {"project_name": "Project"}
    result = _parse_json_manifest(manifest, identity)

    assert result is True
    assert identity["project_name"] == "test-repo"
    assert identity["project_url"] == "https://github.com/user/repo"

def test_parse_json_manifest_repository_dict(tmp_path):
    manifest = tmp_path / "package.json"
    manifest.write_text(json.dumps({
        "name": "test-repo-dict",
        "repository": {
            "type": "git",
            "url": "git+https://github.com/user/repo.git"
        }
    }), encoding='utf-8')

    identity = {"project_name": "Project"}
    result = _parse_json_manifest(manifest, identity)

    assert result is True
    assert identity["project_name"] == "test-repo-dict"
    assert identity["project_url"] == "git+https://github.com/user/repo.git"

def test_markdown_project_overview_full_info():
    # Direct test of _generate_project_overview to ensure we hit the Markdown branches
    stats = {
        'project_name': 'full-project',
        'project_version': '1.0.0',
        'project_license': 'MIT',
        'project_url': 'https://example.com',
        'manifest_source': 'package.json',
        'total_files': 1,
        'total_size_bytes': 100,
        'total_tokens': 20,
        'total_lines': 5,
        'datetime': '2023-01-01 12:00:00',
        'os': 'Linux',
        'python_version': '3.10.0',
        'files_by_language': {'python': 1},
        'tokens_by_language': {'python': 20},
        'lines_by_language': {'python': 5},
        'size_by_language': {'python': 100},
    }

    content = _generate_project_overview(stats, output_format='markdown')

    assert "# Project Overview" in content
    assert "- **Project:** full-project" in content
    assert "- **Version:** 1.0.0" in content
    assert "- **License:** MIT" in content
    assert "- **URL:** https://example.com" in content
    assert "- **Manifest:** package.json" in content
    assert "- **OS:** Linux" in content
    assert "- **Python:** 3.10.0" in content

def test_markdown_project_overview_lines_only():
    # Test the branch where has_lang_lines is True but has_lang_tokens is False
    stats = {
        'project_name': 'lines-project',
        'total_files': 1,
        'total_size_bytes': 100,
        'total_tokens': 0,
        'total_lines': 5,
        'files_by_language': {'text': 1},
        'tokens_by_language': {'text': 0},
        'lines_by_language': {'text': 5},
        'size_by_language': {'text': 100},
    }

    content = _generate_project_overview(stats, output_format='markdown')

    # Check for "% Lines" in language breakdown table
    assert "| % Lines |" in content
    assert "% Lines" in content
