import pytest
from pathlib import Path
from unittest.mock import MagicMock
import logging

from sourcecombine import find_and_combine_files, _generate_table_of_contents
from utils import DEFAULT_CONFIG

import copy
@pytest.fixture
def toc_config(tmp_path):
    config = copy.deepcopy(DEFAULT_CONFIG)
    config['search'] = {'root_folders': [str(tmp_path)]}
    config['output']['table_of_contents'] = True
    config['output']['file'] = str(tmp_path / "output.txt")
    return config

def test_generate_toc_text():
    files = [
        (Path("/root/src/main.py"), Path("/root")),
        (Path("/root/src/utils.py"), Path("/root")),
        (Path("/root/README.md"), Path("/root")),
    ]

    expected = (
        "Table of Contents:\n"
        "- src/main.py\n"
        "- src/utils.py\n"
        "- README.md\n"
        "\n--------------------\n"
    )

    assert _generate_table_of_contents(files, 'text') == expected

def test_generate_toc_markdown():
    files = [
        (Path("/root/src/main.py"), Path("/root")),
        (Path("/root/Hello World.md"), Path("/root")),
    ]

    expected = (
        "## Table of Contents\n"
        "- [src/main.py](#srcmainpy)\n"
        "- [Hello World.md](#hello-worldmd)\n"
    )

    assert _generate_table_of_contents(files, 'markdown') == expected

def test_toc_integration_text(tmp_path, toc_config, caplog):
    # Setup files
    (tmp_path / "a.txt").write_text("content a")
    (tmp_path / "b.txt").write_text("content b")

    output_file = tmp_path / "output.txt"
    toc_config['output']['file'] = str(output_file)

    find_and_combine_files(toc_config, str(output_file))

    content = output_file.read_text(encoding='utf-8')

    assert "Table of Contents:" in content
    assert "- a.txt" in content
    assert "- b.txt" in content
    assert "content a" in content
    assert "content b" in content

def test_toc_integration_markdown(tmp_path, toc_config):
    # Setup files
    (tmp_path / "doc.md").write_text("# Doc")

    output_file = tmp_path / "output.md"
    toc_config['output']['file'] = str(output_file)

    find_and_combine_files(toc_config, str(output_file), output_format='markdown')

    content = output_file.read_text(encoding='utf-8')

    assert "## Table of Contents" in content
    assert "- [doc.md](#docmd)" in content
    assert "# Doc" in content

def test_toc_ignored_in_pairing_mode(tmp_path, toc_config):
    # Setup pairing config
    toc_config['pairing']['enabled'] = True
    toc_config['pairing']['source_extensions'] = ['.c']
    toc_config['pairing']['header_extensions'] = ['.h']

    # TOC should be ignored or raise error if strict, but current implementation ignores it
    # Just ensure it doesn't crash

    output_folder = tmp_path / "out_pair"
    find_and_combine_files(toc_config, str(output_folder))

    # Verification: No output file should be created at 'output.file' location
    # because pairing writes to 'out_folder'
    assert not Path(toc_config['output']['file']).exists()

    # Reset pairing for other tests if config is reused (it is a fixture, but safer to be sure)
    toc_config['pairing']['enabled'] = False

def test_toc_estimate_tokens(tmp_path, toc_config):
    (tmp_path / "a.txt").write_text("content a")

    toc_config['output']['file'] = str(tmp_path / "dummy.txt")

    stats_with_toc = find_and_combine_files(toc_config, None, estimate_tokens=True)

    toc_config['output']['table_of_contents'] = False
    stats_without_toc = find_and_combine_files(toc_config, None, estimate_tokens=True)

    # TOC adds tokens
    assert stats_with_toc['total_tokens'] > stats_without_toc['total_tokens']
