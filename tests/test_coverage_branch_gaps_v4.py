import sys, os; from pathlib import Path; sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch
import pytest

import sourcecombine
import utils


def test_cargo_and_pubspec_project_url_already_set(tmp_path):
    py_cargo_dir = tmp_path / "py_cargo_proj"
    py_cargo_dir.mkdir()
    (py_cargo_dir / "pyproject.toml").write_text('''
[project]
name = "py_cargo"
urls = { Homepage = "https://homepage.com" }
''')
    (py_cargo_dir / "Cargo.toml").write_text('''
[package]
name = "cargo_pkg"
repository = "https://github.com/test/repo"
''')
    res = utils.get_project_identity(str(py_cargo_dir))
    assert res["project_url"] == "https://homepage.com"

    pub_dir = tmp_path / "pub_proj"
    pub_dir.mkdir()
    (pub_dir / "pyproject.toml").write_text('''
[project]
name = "py_pub"
urls = { Homepage = "https://homepage.com" }
''')
    (pub_dir / "pubspec.yaml").write_text('''
name: pub_pkg
repository: https://github.com/test/pubrepo
''')
    res_pub = utils.get_project_identity(str(pub_dir))
    assert res_pub["project_url"] == "https://homepage.com"


def test_readme_description_parsing_empty_lines_and_headers(tmp_path):
    readme_dir = tmp_path / "readme_proj"
    readme_dir.mkdir()
    (readme_dir / "README.md").write_text('''# Project Title

Actual description line that should be extracted as project description.
''')
    res = utils.get_project_identity(str(readme_dir))
    assert res["project_name"] == "Project Title"
    assert res["project_description"] == "Actual description line that should be extracted as project description."


def test_file_processor_header_footer_default_template_override(tmp_path):
    f1 = tmp_path / "file1.py"
    f1.write_text("print('hello')\n")
    out_file = tmp_path / "out.txt"

    default_header = utils.DEFAULT_CONFIG['output']['header_template']
    default_footer = utils.DEFAULT_CONFIG['output']['footer_template']

    config = utils.DEFAULT_CONFIG.copy()
    config['output'] = {
        'file': str(out_file),
        'format': 'mirror',
        'header_template': default_header,
        'footer_template': default_footer,
        'mirror': True,
    }
    config['search'] = {'targets': [str(f1)], 'root_folders': [str(tmp_path)]}

    sourcecombine.find_and_combine_files(config=config, output_path=str(out_file))
    assert config['output']['header_template'] == ""
    assert config['output']['footer_template'] == ""


def test_find_and_combine_files_pairing_max_files_limit(tmp_path):
    d = tmp_path / "src"
    d.mkdir()
    (d / "a.cpp").write_text("code a")
    (d / "a.h").write_text("header a")
    (d / "b.cpp").write_text("code b")
    (d / "b.h").write_text("header b")

    out_file = tmp_path / "out"
    config = utils.DEFAULT_CONFIG.copy()
    config['pairing'] = {
        'enabled': True,
        'source_extensions': ['.cpp'],
        'header_extensions': ['.h'],
    }
    config['output'] = {'file': str(out_file), 'format': 'text'}
    config['search'] = {'targets': [str(d)], 'recursive': True, 'root_folders': [str(d)]}
    config['filters'] = {'sort_by': 'filename', 'max_files': 1}

    stats = sourcecombine.find_and_combine_files(
        config=config,
        output_path=str(out_file)
    )
    assert stats.get('limit_reached') is True
    assert stats['filter_reasons']['file_limit'] == 1


def test_file_processor_max_size_placeholder(tmp_path):
    f1 = tmp_path / "large.py"
    f1.write_text("x = 1\n" * 100)
    out_file = tmp_path / "out.txt"

    config = utils.DEFAULT_CONFIG.copy()
    config['search'] = {'targets': [str(f1)], 'max_size': '10B', 'root_folders': [str(tmp_path)]}
    config['filtering'] = {'record_size_exclusions': True}
    config['output'] = {
        'file': str(out_file),
        'format': 'text',
        'max_size_placeholder': '--- SKIPPED {FILENAME} DUE TO SIZE {SIZE} ---'
    }

    stats = sourcecombine.find_and_combine_files(
        config=config,
        output_path=str(out_file),
        estimate_tokens=True
    )
    assert stats['total_files'] == 1


def test_cli_exclude_file_empty_tokens(monkeypatch, tmp_path):
    f1 = tmp_path / "a.py"
    f1.write_text("print(1)")
    out_file = tmp_path / "out.txt"
    test_args = ['sourcecombine.py', '--exclude-file', 'a.py,,b.py', str(tmp_path), '-o', str(out_file)]
    monkeypatch.setattr(sys, 'argv', test_args)
    with patch("sourcecombine.find_and_combine_files") as mock_combine:
        mock_combine.return_value = {}
        sourcecombine.main()
        cfg = mock_combine.call_args[0][0]
        assert 'a.py' in cfg['filters']['exclusions']['filenames']
        assert 'b.py' in cfg['filters']['exclusions']['filenames']


def test_custom_languages_non_string_keys_and_values(tmp_path):
    f1 = tmp_path / "test.custom"
    f1.write_text("custom code\n")
    out_file = tmp_path / "out.txt"

    config = utils.DEFAULT_CONFIG.copy()
    config['search'] = {
        'targets': [str(f1)],
        'root_folders': [str(tmp_path)],
        'custom_languages': {
            123: "py",
            "custom": "MyLang",
            "other": 456
        }
    }
    config['output'] = {'file': str(out_file), 'format': 'text'}

    stats = sourcecombine.find_and_combine_files(config=config, output_path=str(out_file))
    assert stats['total_files'] == 1


def test_cli_output_file_ending_with_slash(monkeypatch, tmp_path):
    f1 = tmp_path / "test.txt"
    f1.write_text("hello\n")
    out_dir_str = str(tmp_path / "out_dir") + os.sep

    test_args = ['sourcecombine.py', str(f1), '-o', out_dir_str]
    monkeypatch.setattr(sys, 'argv', test_args)

    with patch("sourcecombine.find_and_combine_files") as mock_combine:
        mock_combine.return_value = {}
        sourcecombine.main()
        output_path = mock_combine.call_args[0][1]
        assert output_path.endswith("combined_files.txt")


def test_remote_url_empty_content(tmp_path):
    out_file = tmp_path / "out.txt"
    config = utils.DEFAULT_CONFIG.copy()
    config['search'] = {'targets': ["http://example.com/empty.py"]}
    config['output'] = {'file': str(out_file), 'format': 'text'}

    with patch("utils.read_url_best_effort", return_value=("", None)):
        stats = sourcecombine.find_and_combine_files(
            config=config,
            output_path=str(out_file)
        )
        assert stats.get('total_files', 0) == 0


def test_csv_extraction_parsing_missing_path_and_summary_parentheses():
    csv_content = """path,size_bytes,tokens,lines,modified,sha256,language,content
,100,10,5,,,Python,print('hi')
"""
    files = sourcecombine._parse_combined_content(csv_content, source_name="combined.csv")
    assert len(files) == 0

    summary_block = """<details>
<summary>src/app.py (modified)</summary>
```python
print(1)
```
</details>
"""
    files_sum = sourcecombine._parse_combined_content(summary_block, source_name="summary.md")
    assert len(files_sum) == 1
    assert files_sum[0][0] == "src/app.py"
