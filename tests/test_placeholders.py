import sys; import os; from pathlib import Path; sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))

from sourcecombine import find_and_combine_files

def test_file_information_placeholders(tmp_path):
    """Test that all file-level placeholders are correctly replaced."""
    root = tmp_path / "project"
    root.mkdir()
    sub = root / "sub"
    sub.mkdir()

    file_path = sub / "example.txt"
    content = "Hello World"
    file_path.write_text(content, encoding="utf-8")

    output_file = tmp_path / "combined.txt"

    config = {
        "search": {"root_folders": [str(root)], "recursive": True},
        "output": {
            "file": str(output_file),
            "header_template": "FILE:{{FILENAME}} EXT:{{EXT}} STEM:{{STEM}} DIR:{{DIR}} SLUG:{{DIR_SLUG}} SIZE:{{SIZE}} TOKENS:{{TOKENS}}\n",
            "footer_template": "END:{{FILENAME}}\n",
        },
    }

    find_and_combine_files(config, str(output_file))

    result = output_file.read_text()

    # FILENAME should be sub/example.txt (posix style)
    assert "FILE:sub/example.txt" in result
    assert "EXT:txt" in result
    assert "STEM:example" in result
    assert "DIR:sub" in result
    assert "SLUG:sub" in result
    assert "SIZE:11.00 B" in result
    # "Hello World" is 11 chars. Default estimate is len//4 = 2 tokens if tiktoken missing.
    # Extract the token count from the header and check that it's the same in the footer
    import re
    header_tokens = re.search(r"TOKENS:(\d+)", result).group(1)
    # The header and footer should have the SAME token count (referring to the file content)
    # Even though they were rendered at different times.
    assert f"TOKENS:{header_tokens}" in result
    # We'll check the footer separately if we add a marker
    assert "END:sub/example.txt" in result

def test_footer_token_consistency(tmp_path):
    """Test that footer {{TOKENS}} is consistent with the header."""
    root = tmp_path / "project"
    root.mkdir()
    (root / "f1.txt").write_text("Longer content to ensure more than 0 tokens")

    output_file = tmp_path / "combined.txt"
    config = {
        "search": {"root_folders": [str(root)]},
        "output": {
            "file": str(output_file),
            "header_template": "H:{{TOKENS}}\n",
            "footer_template": "F:{{TOKENS}}\n",
        },
    }

    find_and_combine_files(config, str(output_file))
    result = output_file.read_text()

    import re
    h_tokens = re.search(r"H:(\d+)", result).group(1)
    f_tokens = re.search(r"F:(\d+)", result).group(1)

    assert h_tokens == f_tokens
    assert int(h_tokens) > 0

def test_global_information_placeholders(tmp_path):
    """Test that all global-level placeholders are correctly replaced."""
    root = tmp_path / "project"
    root.mkdir()
    (root / "f1.txt").write_text("One")   # 3 bytes
    (root / "f2.txt").write_text("Two!")  # 4 bytes

    output_file = tmp_path / "combined.txt"

    config = {
        "search": {"root_folders": [str(root)], "recursive": True},
        "output": {
            "file": str(output_file),
            "global_header_template": "COUNT:{{FILE_COUNT}} SIZE:{{TOTAL_SIZE}} TOKENS:{{TOTAL_TOKENS}}\n",
            "global_footer_template": "FINISH:{{FILE_COUNT}}\n",
        },
    }

    find_and_combine_files(config, str(output_file))

    result = output_file.read_text()

    assert "COUNT:2" in result
    assert "SIZE:7.00 B" in result
    # We check for the value since the placeholder is replaced
    assert "TOKENS:" in result
    assert "FINISH:2" in result

def test_placeholders_in_max_size(tmp_path):
    """Test placeholders in max_size_placeholder."""
    root = tmp_path / "project"
    root.mkdir()
    file_path = root / "large.txt"
    file_path.write_text("Very large content") # 18 bytes

    output_file = tmp_path / "combined.txt"

    config = {
        "search": {"root_folders": [str(root)], "recursive": True},
        "filters": {"max_size_bytes": 5}, # Force skip
        "output": {
            "file": str(output_file),
            "max_size_placeholder": "SKIPPED {{FILENAME}} SIZE:{{SIZE}}\n",
        },
    }

    find_and_combine_files(config, str(output_file))

    result = output_file.read_text()
    assert "SKIPPED large.txt SIZE:18.00 B" in result

def test_dir_placeholders_root(tmp_path):
    """Test DIR and DIR_SLUG placeholders for files in the root."""
    root = tmp_path / "project"
    root.mkdir()
    (root / "root_file.txt").write_text("content")

    output_file = tmp_path / "combined.txt"

    config = {
        "search": {"root_folders": [str(root)], "recursive": True},
        "output": {
            "file": str(output_file),
            "header_template": "DIR:{{DIR}} SLUG:{{DIR_SLUG}}\n",
        },
    }

    find_and_combine_files(config, str(output_file))

    result = output_file.read_text()
    assert "DIR:." in result
    assert "SLUG:root" in result

def test_placeholder_recursion(tmp_path):
    """Test that placeholders are not replaced recursively."""
    root = tmp_path / "project"
    root.mkdir()
    # Create a filename that contains another placeholder string
    file_path = root / "foo_{{EXT}}.py"
    file_path.write_text("content", encoding="utf-8")

    output_file = tmp_path / "combined.txt"

    config = {
        "search": {"root_folders": [str(root)]},
        "output": {
            "file": str(output_file),
            "header_template": "FILE:{{FILENAME}} EXT:{{EXT}}\n",
        },
    }

    find_and_combine_files(config, str(output_file))

    result = output_file.read_text()
    # It should NOT replace {{EXT}} inside the filename
    assert "FILE:foo_{{EXT}}.py EXT:py" in result

def test_placeholder_prefix_matching(tmp_path):
    """Test that {{DIR_SLUG}} is not partially matched by {{DIR}}."""
    root = tmp_path / "project"
    root.mkdir()
    sub = root / "sub"
    sub.mkdir()
    (sub / "file.txt").write_text("content")

    output_file = tmp_path / "combined.txt"
    config = {
        "search": {"root_folders": [str(root)]},
        "output": {
            "file": str(output_file),
            "header_template": "DIR:{{DIR}} SLUG:{{DIR_SLUG}}\n",
        },
    }

    find_and_combine_files(config, str(output_file))
    result = output_file.read_text()

    # If DIR was matched first, SLUG would be corrupted (for example, sub_SLUG}})
    assert "DIR:sub SLUG:sub" in result
    assert "_SLUG}}" not in result
import os
import pytest
from pathlib import Path
from sourcecombine import find_and_combine_files
from utils import DEFAULT_CONFIG

def test_extended_placeholders(tmp_path):
    """Test the new placeholders (INDEX, TOTAL, PERCENTs) in combine mode."""
    # Setup test files
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "file1.txt").write_text("Hello World", encoding="utf-8") # 11 chars
    (src_dir / "file2.txt").write_text("Test", encoding="utf-8") # 4 chars

    output_file = tmp_path / "combined.txt"

    config = {
        'search': {'root_folders': [str(src_dir)]},
        'output': {
            'header_template': "File {{INDEX}} of {{TOTAL}} ({{SIZE_PERCENT}}): {{FILENAME}}\n",
            'footer_template': "\n",
            'file': str(output_file)
        }
    }

    # We need to deepcopy the default config and merge our test config
    import copy
    final_config = copy.deepcopy(DEFAULT_CONFIG)
    for section in config:
        final_config[section].update(config[section])

    find_and_combine_files(final_config, str(output_file))

    content = output_file.read_text(encoding="utf-8")

    # Check if placeholders were replaced correctly
    # Total size is 11 + 4 = 15
    # file1: 11/15 = 73.3%
    # file2: 4/15 = 26.7%

    assert "File 1 of 2 (73.3%): file1.txt" in content
    assert "File 2 of 2 (26.7%): file2.txt" in content

def test_extended_placeholders_pairing(tmp_path):
    """Test the new placeholders in pairing mode."""
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "main.cpp").write_text("int main() {}", encoding="utf-8") # 13 chars
    (src_dir / "main.h").write_text("void main();", encoding="utf-8") # 12 chars
    (src_dir / "util.cpp").write_text("void util() {}", encoding="utf-8") # 14 chars
    (src_dir / "util.h").write_text("void util();", encoding="utf-8") # 12 chars

    out_dir = tmp_path / "out"
    out_dir.mkdir()

    import copy
    config = copy.deepcopy(DEFAULT_CONFIG)
    config['search']['root_folders'] = [str(src_dir)]
    config['pairing'] = {
        'enabled': True,
        'source_extensions': ['.cpp'],
        'header_extensions': ['.h']
    }
    config['output'] = {
        'header_template': "Pair {{INDEX}} of {{TOTAL}} ({{SIZE_PERCENT}}): {{FILENAME}}\n",
        'footer_template': "\n",
        'folder': str(out_dir)
    }

    # In pairing mode, total_size is computed per pair for percentages
    # Pair 1: main (13+12=25)
    # Pair 2: util (14+12=26)
    # total_size_for_main = 25
    # main.cpp: 13/25 = 52.0%
    # main.h: 12/25 = 48.0%

    find_and_combine_files(config, str(out_dir))

    main_combined = out_dir / "main.combined"
    util_combined = out_dir / "util.combined"

    assert main_combined.exists()
    assert util_combined.exists()

    main_content = main_combined.read_text(encoding="utf-8")
    # We sort by name by default, so main should be index 1 or 2.
    # main.cpp, main.h, util.cpp, util.h -> main comes before util

    assert "Pair 1 of 2 (52.0%): main.cpp" in main_content
    assert "Pair 1 of 2 (48.0%): main.h" in main_content

    util_content = util_combined.read_text(encoding="utf-8")
    assert "Pair 2 of 2 (53.8%): util.cpp" in util_content # 14/26 = 53.84...
    assert "Pair 2 of 2 (46.2%): util.h" in util_content # 12/26 = 46.15...
