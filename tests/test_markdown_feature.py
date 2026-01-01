import os
import sys
import io
import yaml
import pytest
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))

from sourcecombine import FileProcessor, find_and_combine_files, InvalidConfigError
import utils

def test_file_processor_markdown_ext_placeholder(tmp_path):
    root = tmp_path
    file_path = root / "script.py"
    file_path.write_text("print('hello')", encoding="utf-8")

    config = {
        "processing": {},
        "output": {
            "header_template": "File: {{FILENAME}} ({{EXT}})\n",
            "footer_template": "\nEnd {{EXT}}",
        },
    }

    processor = FileProcessor(config, config["output"])
    out = io.StringIO()
    processor.process_and_write(file_path, root, out)

    result = out.getvalue()
    assert "File: script.py (py)" in result
    assert "End py" in result

def test_file_processor_markdown_ext_placeholder_no_ext(tmp_path):
    root = tmp_path
    file_path = root / "Makefile"
    file_path.write_text("all: build", encoding="utf-8")

    config = {
        "processing": {},
        "output": {
            "header_template": "File: {{FILENAME}} ({{EXT}})\n",
        },
    }

    processor = FileProcessor(config, config["output"])
    out = io.StringIO()
    processor.process_and_write(file_path, root, out)

    result = out.getvalue()
    assert "File: Makefile ()" in result

def test_markdown_format_defaults(tmp_path):
    root = tmp_path
    (root / "script.py").write_text("print('hello')", encoding="utf-8")

    config = {
        "search": {"root_folders": [str(root)]},
        "filters": {},
        "output": {
            "file": str(root / "out.md"),
        },
        "processing": {},
        "pairing": {"enabled": False}
    }

    find_and_combine_files(
        config,
        output_path=str(root / "out.md"),
        output_format="markdown",
        dry_run=False
    )

    content = (root / "out.md").read_text(encoding="utf-8")
    assert "## script.py" in content
    assert "```py" in content
    assert "```\n" in content
    assert "print('hello')" in content

def test_markdown_format_overridden_templates(tmp_path):
    root = tmp_path
    (root / "script.py").write_text("print('hello')", encoding="utf-8")

    config = {
        "search": {"root_folders": [str(root)]},
        "filters": {},
        "output": {
            "file": str(root / "out.md"),
            "header_template": "CUSTOM HEADER {{FILENAME}}\n",
            "footer_template": "CUSTOM FOOTER",
        },
        "processing": {},
        "pairing": {"enabled": False}
    }

    find_and_combine_files(
        config,
        output_path=str(root / "out.md"),
        output_format="markdown",
        dry_run=False
    )

    content = (root / "out.md").read_text(encoding="utf-8")
    assert "CUSTOM HEADER script.py" in content
    assert "CUSTOM FOOTER" in content
    assert "## script.py" not in content  # Should not use default markdown header

def test_markdown_and_pairing(tmp_path):
    root = tmp_path
    (root / "main.cpp").write_text("int main(){}", encoding="utf-8")
    (root / "main.h").write_text("void main();", encoding="utf-8")

    out_folder = root / "out"

    config = {
        "search": {"root_folders": [str(root)]},
        "filters": {},
        "output": {
            "folder": str(out_folder),
            "paired_filename_template": "{{STEM}}.md"
        },
        "processing": {},
        "pairing": {
            "enabled": True,
            "source_extensions": [".cpp"],
            "header_extensions": [".h"]
        }
    }

    find_and_combine_files(
        config,
        output_path=str(out_folder),
        output_format="markdown",
        dry_run=False
    )

    # Check output
    out_file = out_folder / "main.md"
    assert out_file.exists()
    content = out_file.read_text(encoding="utf-8")

    # Should contain markdown headers for both files
    assert "## main.cpp" in content
    assert "```cpp" in content
    assert "## main.h" in content
    assert "```h" in content
