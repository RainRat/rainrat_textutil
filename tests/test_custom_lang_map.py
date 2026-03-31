import pytest
from pathlib import Path
from sourcecombine import find_and_combine_files
from utils import DEFAULT_CONFIG
import copy

def test_custom_lang_map_cli(tmp_path, capsys):
    """Test that --map-lang correctly overrides language detection."""
    # Create a file with a custom extension
    test_file = tmp_path / "test.mjml"
    test_file.write_text("<div>Test</div>", encoding="utf-8")

    config = copy.deepcopy(DEFAULT_CONFIG)
    config['search']['root_folders'] = [str(tmp_path)]
    # Manually inject the mapping as if from CLI
    config['search']['custom_languages'] = {".mjml": "html"}

    output_file = tmp_path / "combined.md"

    # We use markdown format to see the language tag in the header
    find_and_combine_files(
        config,
        str(output_file),
        output_format='markdown'
    )

    content = output_file.read_text(encoding="utf-8")
    # Default header for markdown includes ```{{LANG}}
    assert "```html" in content
    assert "test.mjml" in content

def test_custom_lang_map_config(tmp_path):
    """Test that custom_languages in config correctly maps filenames."""
    # Create a file with a specific name
    test_file = tmp_path / "VERSION"
    test_file.write_text("1.0.0", encoding="utf-8")

    config = copy.deepcopy(DEFAULT_CONFIG)
    config['search']['root_folders'] = [str(tmp_path)]
    config['search']['custom_languages'] = {"version": "text"}

    output_file = tmp_path / "combined.md"

    find_and_combine_files(
        config,
        str(output_file),
        output_format='markdown'
    )

    content = output_file.read_text(encoding="utf-8")
    assert "```text" in content
    assert "VERSION" in content

def test_custom_lang_map_no_dot(tmp_path):
    """Test that mapping without a dot also works for extensions."""
    test_file = tmp_path / "test.inc"
    test_file.write_text("// some code", encoding="utf-8")

    config = copy.deepcopy(DEFAULT_CONFIG)
    config['search']['root_folders'] = [str(tmp_path)]
    config['search']['custom_languages'] = {"inc": "cpp"}

    output_file = tmp_path / "combined.md"

    find_and_combine_files(
        config,
        str(output_file),
        output_format='markdown'
    )

    content = output_file.read_text(encoding="utf-8")
    assert "```cpp" in content
    assert "test.inc" in content

def test_custom_lang_map_precedence(tmp_path):
    """Test that custom mapping takes precedence over default mapping."""
    test_file = tmp_path / "test.py"
    test_file.write_text("print('hello')", encoding="utf-8")

    config = copy.deepcopy(DEFAULT_CONFIG)
    config['search']['root_folders'] = [str(tmp_path)]
    # Override .py to something else
    config['search']['custom_languages'] = {".py": "custom-python"}

    output_file = tmp_path / "combined.md"

    find_and_combine_files(
        config,
        str(output_file),
        output_format='markdown'
    )

    content = output_file.read_text(encoding="utf-8")
    assert "```custom-python" in content
