import sys
from pathlib import Path

# Add current directory to sys.path to import utils
sys.path.append(str(Path(__file__).parent.parent))

from utils import read_file_best_effort

def test_read_file_utf16be_no_bom(tmp_path):
    """
    Verify that a UTF-16BE file without a BOM is correctly decoded.
    We use a string long enough for reliable detection.
    """
    f = tmp_path / "utf16be_no_bom.txt"
    content = "Hello UTF-16BE - This is a long enough sample."
    # Encode as Big Endian without BOM
    encoded = content.encode('utf-16-be')
    f.write_bytes(encoded)

    decoded_content, encoding = read_file_best_effort(f)

    assert decoded_content == content
    assert "utf" in encoding.lower()
    assert "16" in encoding
    assert "be" in encoding.lower()

def test_read_file_utf16le_no_bom(tmp_path):
    """
    Verify that a UTF-16LE file without a BOM is correctly decoded.
    """
    f = tmp_path / "utf16le_no_bom.txt"
    content = "Hello UTF-16LE - This is a long enough sample."
    # Encode as Little Endian without BOM
    encoded = content.encode('utf-16-le')
    f.write_bytes(encoded)

    decoded_content, encoding = read_file_best_effort(f)

    assert decoded_content == content
    assert "utf" in encoding.lower()
    assert "16" in encoding
    assert "le" in encoding.lower()
