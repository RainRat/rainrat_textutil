import os
import shutil
import pytest
from pathlib import Path
import sourcecombine
from utils import DEFAULT_CONFIG
import copy

@pytest.fixture
def test_env(tmp_path):
    root = tmp_path / "test_root"
    root.mkdir()
    return root

def test_pairing_stats_no_pairs(test_env):
    # Setup: main.cpp and orphan.cpp, no header.
    (test_env / "main.cpp").write_text("int main() {}")
    (test_env / "orphan.cpp").write_text("int orphan() {}")

    config = copy.deepcopy(DEFAULT_CONFIG)
    config['search']['root_folders'] = [str(test_env)]
    config['pairing']['enabled'] = True
    config['pairing']['source_extensions'] = [".cpp"]
    config['pairing']['header_extensions'] = [".h"]
    config['pairing']['include_mismatched'] = False

    # We expect 0 files in stats because no pair was formed
    stats = sourcecombine.find_and_combine_files(config, output_path="out_dir", dry_run=True)

    assert stats['total_files'] == 0
    assert stats['filter_reasons'].get('unpaired') == 2

def test_pairing_stats_one_pair(test_env):
    # Setup: main.cpp, main.h (pair) and orphan.cpp (unpaired)
    (test_env / "main.cpp").write_text("int main() {}")
    (test_env / "main.h").write_text("int main();")
    (test_env / "orphan.cpp").write_text("int orphan() {}")

    config = copy.deepcopy(DEFAULT_CONFIG)
    config['search']['root_folders'] = [str(test_env)]
    config['pairing']['enabled'] = True
    config['pairing']['source_extensions'] = [".cpp"]
    config['pairing']['header_extensions'] = [".h"]
    config['pairing']['include_mismatched'] = False

    # We expect 2 files in stats because only main.cpp and main.h are paired
    stats = sourcecombine.find_and_combine_files(config, output_path="out_dir", dry_run=True)

    assert stats['total_files'] == 2
    assert stats['filter_reasons'].get('unpaired') == 1
