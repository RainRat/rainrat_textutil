import io
import re
from pathlib import Path
from unittest.mock import patch
from utils import get_project_identity
from sourcecombine import (
    _pair_files,
    filter_file_paths,
    FileProcessor,
    _generate_tree_string,
    _generate_table_of_contents,
    find_and_combine_files,
)


def test_get_project_identity_cargo_no_homepage(tmp_path):
    cargo = tmp_path / "Cargo.toml"
    cargo.write_text(
        '[package]\nname = "mycargo"\nrepository = "https://github.com/rust/cargo"\n',
        encoding="utf-8",
    )
    identity = get_project_identity(tmp_path)
    assert identity["project_url"] == "https://github.com/rust/cargo"


def test_get_project_identity_pubspec_no_homepage(tmp_path):
    pubspec = tmp_path / "pubspec.yaml"
    pubspec.write_text(
        'name: mypubspec\nrepository: https://github.com/flutter/flutter\n',
        encoding="utf-8",
    )
    identity = get_project_identity(tmp_path)
    assert identity["project_url"] == "https://github.com/flutter/flutter"


def test_get_project_identity_cargo_and_pubspec_prepopulated_url_branch(tmp_path):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[project]\nurls = { homepage = "https://example.com" }\n',
        encoding="utf-8",
    )
    cargo = tmp_path / "Cargo.toml"
    cargo.write_text(
        '[package]\nname = "mycargo"\nrepository = "https://github.com/rust/cargo"\n',
        encoding="utf-8",
    )
    pubspec = tmp_path / "pubspec.yaml"
    pubspec.write_text(
        'name: mypubspec\nrepository: https://github.com/flutter/flutter\n',
        encoding="utf-8",
    )

    real_search = re.search
    call_cnt = [0]

    def search_mock(pattern, string, *args, **kwargs):
        res = real_search(pattern, string, *args, **kwargs)
        if r'urls?\s*=\s*\{' in pattern and res:
            call_cnt[0] += 1
            if call_cnt[0] == 1:
                return res
        if call_cnt[0] == 1 and pattern.startswith(r'\[project\.urls\]'):
            raise RuntimeError("Pyproject exception after setting project_url")
        return res

    with patch("re.search", side_effect=search_mock):
        identity = get_project_identity(tmp_path)
        assert identity["project_url"] == "https://example.com"


def test_get_project_identity_readme_empty_remaining(tmp_path):
    readme = tmp_path / "README.md"
    readme.write_text("# Title Only\n", encoding="utf-8")
    identity = get_project_identity(tmp_path)
    assert identity["project_name"] == "Title Only"
    assert identity["project_description"] == ""


def test_get_project_identity_readme_subheader_break(tmp_path):
    readme = tmp_path / "README.md"
    readme.write_text("# Title\n\n## Section 1\nDescription text\n", encoding="utf-8")
    identity = get_project_identity(tmp_path)
    assert identity["project_name"] == "Title"
    assert identity["project_description"] == ""


def test_pair_files_same_source_and_header(tmp_path):
    f1 = tmp_path / "src" / "main.cpp"
    f1.parent.mkdir(parents=True)
    f1.write_text("int main() {}", encoding="utf-8")

    paired = _pair_files(
        [f1],
        source_exts=[".cpp"],
        header_exts=[".cpp"],
        include_mismatched=False,
        root_path=tmp_path,
    )
    assert len(paired) == 1
    assert paired[0][1] == [f1]


def test_filter_file_paths_reasons_none(tmp_path):
    f = tmp_path / "test.txt"
    f.write_text("hello", encoding="utf-8")
    filtered, size_excluded = filter_file_paths(
        [f],
        filter_opts={"exclusions": {"filenames": ["test.txt"]}},
        search_opts={},
        root_path=tmp_path,
        record_size_exclusions=True,
        stats=None,
    )
    assert filtered == []


def test_file_processor_emit_entry_modified_none():
    processor = FileProcessor(config={}, output_opts={"format": "json"})
    buf = io.StringIO()
    processor._emit_entry(
        buf,
        content="hello",
        relative_path=Path("test.txt"),
        file_size=5,
        token_count=1,
        is_approx=False,
        line_count=1,
        modified=None,
    )
    out = buf.getvalue()
    assert '"modified"' not in out


def test_file_processor_write_max_size_placeholder_no_file_path():
    processor = FileProcessor(config={}, output_opts={})
    buf = io.StringIO()
    processor.write_max_size_placeholder(
        file_path=None,
        root_path=Path("."),
        outfile=buf,
    )


def test_generate_tree_string_falsy_information(tmp_path):
    f = tmp_path / "a" / "b.py"
    f.parent.mkdir(parents=True)
    f.write_text("pass", encoding="utf-8")
    res = _generate_tree_string(
        [f],
        tmp_path,
        output_format="text",
        include_header=False,
        information={f: {}},
    )
    assert "b.py" in res


def test_generate_table_of_contents_path_not_in_information(tmp_path):
    f = tmp_path / "a.py"
    res = _generate_table_of_contents(
        [(f, tmp_path)], output_format="markdown", information={}
    )
    assert "a.py" in res


def test_find_and_combine_files_empty_tree_view(tmp_path):
    config = {
        "output": {"format": "text", "tree_view": True, "destination": "stdout"},
        "search": {"targets": [str(tmp_path)]},
        "filtering": {"exclusions": {"filenames": ["empty.txt"]}},
    }
    f = tmp_path / "empty.txt"
    f.write_text("hello", encoding="utf-8")
    res = find_and_combine_files(config=config, output_path=None, dry_run=True, tree_view=True)
    assert res is not None


def test_find_and_combine_files_analyze_falsy_max_size_placeholder(tmp_path):
    f = tmp_path / "big.txt"
    f.write_text("1234567890", encoding="utf-8")
    config = {
        "output": {
            "format": "text",
            "destination": "stdout",
            "max_size_placeholder": "",
        },
        "search": {"targets": [str(tmp_path)]},
        "filtering": {"max_size": "5B"},
    }
    res = find_and_combine_files(config=config, output_path=None, dry_run=True)
    assert res is not None
