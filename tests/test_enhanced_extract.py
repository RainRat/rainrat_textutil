import json
from sourcecombine import extract_files

def test_extract_metadata_json(tmp_path):
    """Test that extraction from JSON preserves metadata."""
    data = [
        {
            "path": "test.py",
            "content": "print('hello')",
            "tokens": 5,
            "size_bytes": 14,
            "lines": 1,
            "tokens_is_approx": False
        }
    ]
    content = json.dumps(data)

    stats = extract_files(content, tmp_path, dry_run=True)

    assert stats['total_files'] == 1
    assert stats['total_tokens'] == 5
    assert stats['total_size_bytes'] == 14
    assert stats['total_lines'] == 1
    assert stats['top_files'][0] == (5, 14, "test.py")

def test_extract_metadata_xml(tmp_path):
    """Test that extraction from XML preserves metadata."""
    content = """
<repository>
<file path="test.py" tokens="5" size="14 B" lines="1">
print('hello')
</file>
</repository>
    """

    stats = extract_files(content, tmp_path, dry_run=True)

    assert stats['total_files'] == 1
    assert stats['total_tokens'] == 5
    assert stats['total_size_bytes'] == 14
    assert stats['total_lines'] == 1

def test_extract_sorting_size(tmp_path):
    """Test that extracted files can be sorted by size."""
    data = [
        {"path": "small.txt", "content": "a", "size_bytes": 1},
        {"path": "large.txt", "content": "abc", "size_bytes": 3}
    ]
    content = json.dumps(data)

    # Sort descending by size
    stats = extract_files(content, tmp_path, dry_run=True, sort_by='size', sort_reverse=True)

    # Check top_files order
    # top_files stores (tokens, size, path)
    assert stats['top_files'][0][2] == "large.txt"
    assert stats['top_files'][1][2] == "small.txt"

def test_extract_sorting_tokens(tmp_path):
    """Test that extracted files can be sorted by tokens."""
    data = [
        {"path": "few.txt", "content": "a", "tokens": 1},
        {"path": "many.txt", "content": "abc", "tokens": 100}
    ]
    content = json.dumps(data)

    # Sort descending by tokens
    stats = extract_files(content, tmp_path, dry_run=True, sort_by='tokens', sort_reverse=True)

    assert stats['top_files'][0][2] == "many.txt"
    assert stats['top_files'][1][2] == "few.txt"

def test_extract_token_estimation(tmp_path):
    """Test that extraction can estimate tokens if they are missing."""
    data = [
        {"path": "test.txt", "content": "This is a test with some words."}
    ]
    content = json.dumps(data)

    # Run with token estimation enabled
    stats = extract_files(content, tmp_path, dry_run=True, estimate_tokens=True)

    assert stats['total_tokens'] > 0
    assert stats['top_files'][0][0] > 0
    # Since tiktoken is installed in this environment, it shouldn't be approx if it works,
    # but we'll accept either as long as it's > 0.

def test_extract_tree_with_metadata(tmp_path, capsys):
    """Test that the tree view during extraction includes metadata."""
    data = [
        {"path": "dir/file.py", "content": "print('hi')", "tokens": 10, "size_bytes": 10, "lines": 1}
    ]
    content = json.dumps(data)

    extract_files(content, tmp_path, dry_run=True, tree_view=True, source_name="source")

    captured = capsys.readouterr()
    # On some systems, the trailing slash might be handled differently by PurePath/Path
    # based on whether it's Windows or Posix, but SourceCombine tries to normalize.
    assert "dir" in captured.out
    assert "file.py" in captured.out
    assert "10 tokens" in captured.out
    assert "10.00 B" in captured.out
