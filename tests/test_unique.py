import pytest
from sourcecombine import find_and_combine_files, extract_files
from utils import DEFAULT_CONFIG

@pytest.fixture
def test_dir(tmp_path):
    d = tmp_path / "test_dedup"
    d.mkdir()
    return d

def test_path_deduplication(test_dir):
    # Setup files
    file1 = test_dir / "file1.txt"
    file1.write_text("content1")

    subdir = test_dir / "subdir"
    subdir.mkdir()
    file2 = subdir / "file2.txt"
    file2.write_text("content2")

    config = DEFAULT_CONFIG.copy()
    config['search'] = {
        'root_folders': [str(test_dir), str(subdir)],
        'recursive': True
    }
    config['filters'] = {
        'unique': True,
        'exclusions': {'filenames': [], 'folders': []}
    }
    config['output'] = {'sort_by': 'name'}

    # Run combine
    stats = find_and_combine_files(config, output_path=str(test_dir / "out.txt"))

    # file1.txt and subdir/file2.txt should be included.
    # The second target (subdir) also contains file2.txt, which should be skipped.
    assert stats['total_files'] == 2
    assert stats['filter_reasons'].get('duplicate_path') == 1

def test_content_deduplication(test_dir):
    # Setup files with identical content
    file1 = test_dir / "file1.txt"
    file1.write_text("duplicate content")
    file2 = test_dir / "file2.txt"
    file2.write_text("duplicate content")
    file3 = test_dir / "file3.txt"
    file3.write_text("unique content")

    config = DEFAULT_CONFIG.copy()
    config['search'] = {
        'root_folders': [str(test_dir)],
        'recursive': True
    }
    config['filters'] = {
        'unique': True,
        'exclusions': {'filenames': [], 'folders': []}
    }
    config['output'] = {'sort_by': 'name'}

    # Run combine
    stats = find_and_combine_files(config, output_path=str(test_dir / "out.txt"))

    # Only one of the duplicate files and the unique file should be included.
    assert stats['total_files'] == 2
    assert stats['filter_reasons'].get('duplicate_content') == 1

def test_extraction_deduplication(test_dir):
    # Setup combined content with duplicate files
    combined_content = """--- file1.txt ---
duplicate content
--- end file1.txt ---
--- file2.txt ---
duplicate content
--- end file2.txt ---
--- file3.txt ---
unique content
--- end file3.txt ---
"""
    combined_file = test_dir / "combined.txt"
    combined_file.write_text(combined_content)

    config = DEFAULT_CONFIG.copy()
    config['filters'] = {'unique': True}

    extract_dir = test_dir / "extracted"
    extract_dir.mkdir()

    stats = extract_files([(str(combined_file), combined_content)], str(extract_dir), config=config)

    assert stats['total_files'] == 2
    assert stats['filter_reasons'].get('duplicate_content') == 1

    # Check that only 2 files were actually created
    created_files = list(extract_dir.rglob("*"))
    created_files = [f for f in created_files if f.is_file()]
    assert len(created_files) == 2
