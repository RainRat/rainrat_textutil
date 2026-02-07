import sys
from pathlib import Path
import pytest
import xml.etree.ElementTree as ET

# Ensure repo root is on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sourcecombine import find_and_combine_files

def test_xml_output_defaults(tmp_path):
    # Setup
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "a.py").write_text("print('a')", encoding="utf-8")

    output_file = tmp_path / "output.xml"

    config = {
        'search': {'root_folders': [str(src_dir)]},
        'filters': {},
        'output': {'file': str(output_file)},
        'pairing': {'enabled': False}
    }

    # Execute
    stats = find_and_combine_files(config, str(output_file), output_format='xml')

    # Verify
    assert stats['total_files'] == 1

    content = output_file.read_text(encoding="utf-8")
    assert "<repository>" in content
    assert '<file path="a.py">' in content
    assert "print('a')" in content
    assert "</file>" in content
    assert "</repository>" in content

    # Verify it's valid XML
    root = ET.fromstring(content)
    assert root.tag == "repository"
    file_node = root.find("file")
    assert file_node is not None
    assert file_node.attrib["path"] == "a.py"
    assert file_node.text.strip() == "print('a')"

def test_xml_output_escaping(tmp_path):
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "a.xml").write_text("<tag>content & more</tag>", encoding="utf-8")

    output_file = tmp_path / "output.xml"

    config = {
        'search': {'root_folders': [str(src_dir)]},
        'output': {'file': str(output_file)},
        'pairing': {'enabled': False}
    }

    find_and_combine_files(config, str(output_file), output_format='xml')

    content = output_file.read_text(encoding="utf-8")
    # Content should be escaped
    assert "&lt;tag&gt;content &amp; more&lt;/tag&gt;" in content

    # Valid XML check
    root = ET.fromstring(content)
    file_node = root.find("file")
    assert file_node.text.strip() == "<tag>content & more</tag>"

def test_xml_output_overridden_templates(tmp_path):
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "a.txt").write_text("content", encoding="utf-8")

    output_file = tmp_path / "output.xml"

    config = {
        'search': {'root_folders': [str(src_dir)]},
        'output': {
            'file': str(output_file),
            'header_template': '<custom_file name="{{FILENAME}}">\n',
            'footer_template': '</custom_file>\n',
            'global_header_template': '<custom_repo>\n',
            'global_footer_template': '</custom_repo>\n'
        },
        'pairing': {'enabled': False}
    }

    find_and_combine_files(config, str(output_file), output_format='xml')

    content = output_file.read_text(encoding="utf-8")
    assert "<custom_repo>" in content
    assert '<custom_file name="a.txt">' in content
    assert "content" in content
    assert "</custom_file>" in content
    assert "</custom_repo>" in content

def test_xml_output_max_size_placeholder(tmp_path):
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    large_file = src_dir / "large.txt"
    large_file.write_text("A" * 100, encoding="utf-8")

    config = {
        'search': {'root_folders': [str(src_dir)]},
        'filters': {'max_size_bytes': 10},
        'output': {
            'file': str(tmp_path / "output.xml"),
            'max_size_placeholder': 'SKIPPED {{FILENAME}} & more'
        },
        'pairing': {'enabled': False}
    }

    find_and_combine_files(config, str(tmp_path / "output.xml"), output_format='xml')

    content = (tmp_path / "output.xml").read_text(encoding="utf-8")
    # Placeholder should be escaped for XML
    assert "SKIPPED large.txt &amp; more" in content

    # Valid XML check
    root = ET.fromstring(content)
    file_node = root.find("file")
    assert file_node.text.strip() == "SKIPPED large.txt & more"

def test_xml_output_with_line_numbers(tmp_path):
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "a.txt").write_text("line1\nline2", encoding="utf-8")

    output_file = tmp_path / "output.xml"

    config = {
        'search': {'root_folders': [str(src_dir)]},
        'output': {
            'file': str(output_file),
            'add_line_numbers': True
        },
        'pairing': {'enabled': False}
    }

    find_and_combine_files(config, str(output_file), output_format='xml')

    content = output_file.read_text(encoding="utf-8")
    assert "1: line1" in content
    assert "2: line2" in content

    # Valid XML check
    root = ET.fromstring(content)
    file_node = root.find("file")
    assert "1: line1" in file_node.text
    assert "2: line2" in file_node.text
