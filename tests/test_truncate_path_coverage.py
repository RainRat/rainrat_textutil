import os
import sys

# Adjust sys.path to include the project root
sys.path.insert(0, os.fspath(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sourcecombine import _truncate_path

def test_truncate_path_less_than_four_width():
    assert _truncate_path("longpath/filename.txt", 3) == "lon"
    assert _truncate_path("longpath/filename.txt", 2) == "lo"
    assert _truncate_path("a", 3) == "a"

def test_truncate_path_ten_or_less_width():
    assert _truncate_path("12345678901", 10) == "1234567..."
    assert _truncate_path("1234567890", 10) == "1234567890"
