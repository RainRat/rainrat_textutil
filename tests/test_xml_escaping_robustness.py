import sys
from pathlib import Path
import pytest
import xml.etree.ElementTree as ET

# Ensure repo root is on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sourcecombine import find_and_combine_files

def test_xml_output_filename_with_quotes(tmp_path):
    """Verify that filenames with quotes are correctly escaped in XML output."""
    src_dir = tmp_path / "src"
    src_dir.mkdir()

    # Filename with double and single quotes
    # XML attributes are typically enclosed in double quotes, so double quotes MUST be escaped.
    # Single quotes should also be escaped for robustness.
    special_filename = 'file_with_"double"_and_\'single\'_quotes.txt'
    (src_dir / special_filename).write_text("content", encoding="utf-8")

    output_file = tmp_path / "output.xml"

    config = {
        'search': {'root_folders': [str(src_dir)]},
        'output': {'file': str(output_file)},
        'pairing': {'enabled': False}
    }

    # Execute
    find_and_combine_files(config, str(output_file), output_format='xml')

    content = output_file.read_text(encoding="utf-8")

    # Check if the problematic characters are present in their raw form (they shouldn't be in the attribute)
    # The default template is <file path="{{FILENAME}}">
    # If not escaped, it would look like <file path="file_with_"double"_and_'single'_quotes.txt">

    # Verify it's valid XML by parsing it
    try:
        root = ET.fromstring(content)
        file_node = root.find("file")
        assert file_node is not None
        assert file_node.attrib["path"] == special_filename
    except ET.ParseError as e:
        pytest.fail(f"XML parsing failed due to incorrect escaping: {e}\nContent: {content}")

def test_xml_output_content_with_quotes(tmp_path):
    """Verify that file content with quotes is correctly handled (though less critical than attributes)."""
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "test.txt").write_text('Text with "quotes" and <tags>.', encoding="utf-8")

    output_file = tmp_path / "output.xml"

    config = {
        'search': {'root_folders': [str(src_dir)]},
        'output': {'file': str(output_file)},
        'pairing': {'enabled': False}
    }

    find_and_combine_files(config, str(output_file), output_format='xml')

    content = output_file.read_text(encoding="utf-8")

    # Verify it's valid XML
    root = ET.fromstring(content)
    file_node = root.find("file")
    assert file_node.text.strip() == 'Text with "quotes" and <tags>.'
