import pytest
import utils
import sourcecombine
from unittest.mock import patch
import copy

def test_validate_search_not_dict():
    config = {'search': 'not a dict'}
    with pytest.raises(utils.InvalidConfigError, match="'search' section must be a dictionary."):
        utils._validate_search_section(config)

def test_validate_filters_invalid_max_total_size():
    config = {'filters': {'max_total_size_bytes': -1}}
    with pytest.raises(utils.InvalidConfigError, match="filters.max_total_size_bytes must be 0 or more"):
        utils._validate_filters_section(config)

def test_validate_filters_invalid_max_total_lines():
    config = {'filters': {'max_total_lines': -1}}
    with pytest.raises(utils.InvalidConfigError, match="filters.max_total_lines must be 0 or more"):
        utils._validate_filters_section(config)

def test_validate_pairing_not_dict():
    config = {'pairing': 'not a dict'}
    with pytest.raises(utils.InvalidConfigError, match="'pairing' section must be a dictionary."):
        utils._validate_pairing_section(config)

def test_validate_filters_search_not_dict():
    # Trigger line 451 in utils.py
    config = {'filters': {}, 'search': None}
    utils._validate_filters_section(config)
    assert isinstance(config['search'], dict)

def test_main_output_is_dir(tmp_path):
    output_dir = tmp_path / "output_dir"
    output_dir.mkdir()

    test_file = tmp_path / "test.py"
    test_file.write_text("print('hello')", encoding='utf-8')

    # Test that specifying a directory now works via main()
    with patch('sys.argv', ['sourcecombine.py', str(test_file), '-o', str(output_dir)]):
        with patch('sourcecombine.print_system_info'): # Avoid extra output
            try:
                sourcecombine.main()
            except SystemExit as e:
                assert e.code in (0, None)

    assert (output_dir / "combined_files.txt").exists()

def test_find_and_combine_files_output_is_dir_directly(tmp_path):
    # If called directly with a directory, it should now fail with IsADirectoryError
    # (or we could make it handle it, but for now we verify the old error is gone)
    output_dir = tmp_path / "output_dir_direct"
    output_dir.mkdir()
    config = copy.deepcopy(utils.DEFAULT_CONFIG)

    with pytest.raises(IsADirectoryError):
        sourcecombine.find_and_combine_files(
            config,
            output_path=str(output_dir),
            output_format='text'
        )

def test_apply_in_place_functional(tmp_path):
    # Setup a file to be processed
    test_file = tmp_path / "test.txt"
    test_file.write_text("line1\n\n\nline2", encoding="utf-8")

    # Configuration to apply in place with compact whitespace
    config = copy.deepcopy(utils.DEFAULT_CONFIG)
    config['processing'] = {
        'apply_in_place': True,
        'create_backups': True,
        'compact_whitespace': True,
        'compact_whitespace_groups': {'compact_blank_lines': True}
    }
    config['search']['root_folders'] = [str(tmp_path)]

    # Run find_and_combine_files
    sourcecombine.find_and_combine_files(
        config,
        output_path=str(tmp_path / "combined.txt")
    )

    # Verify the file was updated
    updated_content = test_file.read_text(encoding="utf-8")
    assert "line1\n\nline2" in updated_content
    assert "\n\n\n" not in updated_content

    # Verify backup was created
    backup_file = tmp_path / "test.txt.bak"
    assert backup_file.exists()
    assert backup_file.read_text(encoding="utf-8") == "line1\n\n\nline2"
