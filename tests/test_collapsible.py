import sys
from pathlib import Path
from sourcecombine import find_and_combine_files, extract_files, verify_files, main

def test_combine_markdown_with_collapsible(tmp_path):
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    file_a = src_dir / "a.py"
    file_a.write_text("print('hello')", encoding="utf-8")

    config = {
        "search": {
            "root_folders": [str(src_dir)],
        },
        "filters": {},
        "output": {
            "format": "markdown",
            "collapsible": True,
            "header_template": "## {{FILENAME}}\n\n```{{LANG}}\n",
            "footer_template": "\n```\n\n",
        }
    }

    output_file = tmp_path / "combined.md"

    stats = find_and_combine_files(config, str(output_file), output_format="markdown")

    combined_content = output_file.read_text(encoding="utf-8")

    assert "<details><summary><b>a.py</b>" in combined_content
    assert "</details>" in combined_content
    assert "print('hello')" in combined_content

def test_extract_collapsible_markdown(tmp_path):
    combined_content = """<details><summary><b>libs/b.py</b> (1 line • 25 B)</summary>

## libs/b.py

```python
def foo(): pass
```

</details>
"""
    sources = [("combined.md", combined_content)]
    out_dir = tmp_path / "restored"

    stats = extract_files(sources, str(out_dir))

    restored_file = out_dir / "libs" / "b.py"
    assert restored_file.is_file()
    assert restored_file.read_text(encoding="utf-8").strip() == "def foo(): pass"

def test_verify_collapsible_markdown(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    file_b = root / "libs" / "b.py"
    file_b.parent.mkdir(parents=True, exist_ok=True)
    file_b.write_text("def foo(): pass", encoding="utf-8")

    combined_content = """<details><summary><b>libs/b.py</b> (1 line • 25 B)</summary>

## libs/b.py

```python
def foo(): pass
```

</details>
"""
    sources = [("combined.md", combined_content)]

    results = verify_files(sources, root_folder=root)

    assert results["matches"] == 1
    assert results["mismatches"] == 0
    assert results["missing"] == 0

def test_extract_collapsible_markdown_without_code_blocks(tmp_path):
    combined_content = """<details><summary><b>simple.txt</b></summary>
raw simple file content here without any backticks
</details>
"""
    sources = [("combined.md", combined_content)]
    out_dir = tmp_path / "restored"

    stats = extract_files(sources, str(out_dir))

    restored_file = out_dir / "simple.txt"
    assert restored_file.is_file()
    assert restored_file.read_text(encoding="utf-8").strip() == "raw simple file content here without any backticks"

def test_cli_integration_with_collapsible_flag(tmp_path, monkeypatch, capsys):
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    file_a = src_dir / "a.py"
    file_a.write_text("print('hello')", encoding="utf-8")

    output_file = tmp_path / "combined.md"

    monkeypatch.setattr(sys, "argv", [
        "sourcecombine.py",
        str(src_dir),
        "--output", str(output_file),
        "--format", "markdown",
        "--collapsible"
    ])

    try:
        main()
    except SystemExit as e:
        assert e.code == 0

    combined_content = output_file.read_text(encoding="utf-8")
    assert "<details><summary><b>a.py</b>" in combined_content
    assert "</details>" in combined_content
