import pytest
from sourcecombine import find_and_combine_files
from utils import DEFAULT_CONFIG, validate_config

@pytest.fixture
def test_dir(tmp_path):
    d = tmp_path / "test_ext_filter"
    d.mkdir()
    (d / "file.py").write_text("print(1)")
    (d / "file.js").write_text("console.log(1)")
    (d / "file.txt").write_text("hello")
    return d

def test_extension_inclusion_cli(test_dir):
    config = DEFAULT_CONFIG.copy()
    config['search'] = {'root_folders': [str(test_dir)]}

    # Mock args for extension inclusion
    class Args:
        extension = ['py', '.js']
        exclude_extension = []
        language = []
        exclude_language = []
        map_lang = []

    import sourcecombine
    # We need to manually apply what main() does to config before calling find_and_combine_files
    search = config['search']
    search['allowed_extensions'] = Args.extension

    validate_config(config)

    stats = find_and_combine_files(config, output_path=None, dry_run=True)

    # Should include .py and .js, but not .txt
    assert stats['total_files'] == 2
    # Verify they are the right ones
    paths = [f[2] for f in stats['top_files']]
    assert any(p.endswith('file.py') for p in paths)
    assert any(p.endswith('file.js') for p in paths)
    assert not any(p.endswith('file.txt') for p in paths)

def test_extension_exclusion_cli(test_dir):
    config = DEFAULT_CONFIG.copy()
    config['search'] = {'root_folders': [str(test_dir)]}

    # Mock args for extension exclusion
    class Args:
        extension = []
        exclude_extension = ['txt', '.js']

    search = config['search']
    search['exclude_extensions'] = Args.exclude_extension

    validate_config(config)

    stats = find_and_combine_files(config, output_path=None, dry_run=True)

    # Should include .py, but not .js or .txt
    assert stats['total_files'] == 1
    paths = [f[2] for f in stats['top_files']]
    assert any(p.endswith('file.py') for p in paths)
    assert not any(p.endswith('file.js') for p in paths)
    assert not any(p.endswith('file.txt') for p in paths)
    assert stats['filter_reasons'].get('extension_excluded') == 2
