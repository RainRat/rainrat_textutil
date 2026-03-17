import json
from sourcecombine import extract_files

def test_extract_sorting_depth_descending(tmp_path):
    data = [
        {"path": "a/b/c/file.txt", "content": "deep", "size_bytes": 4},
        {"path": "file.txt", "content": "shallow", "size_bytes": 7}
    ]
    content = json.dumps(data)

    stats = extract_files(content, tmp_path, dry_run=True, sort_by='depth', sort_reverse=True)

    assert stats['top_files'][0][2] == "a/b/c/file.txt"
    assert stats['top_files'][1][2] == "file.txt"

def test_extract_sorting_depth_ascending(tmp_path):
    data = [
        {"path": "a/b/c/file.txt", "content": "deep", "size_bytes": 4},
        {"path": "file.txt", "content": "shallow", "size_bytes": 7}
    ]
    content = json.dumps(data)

    stats = extract_files(content, tmp_path, dry_run=True, sort_by='depth', sort_reverse=False)

    assert stats['top_files'][0][2] == "file.txt"
    assert stats['top_files'][1][2] == "a/b/c/file.txt"

def test_extract_sorting_modified_fallback_to_path(tmp_path):
    data = [
        {"path": "z.txt", "content": "z", "size_bytes": 1},
        {"path": "a.txt", "content": "a", "size_bytes": 1}
    ]
    content = json.dumps(data)

    stats = extract_files(content, tmp_path, dry_run=True, sort_by='modified')

    assert stats['top_files'][0][2] == "a.txt"
    assert stats['top_files'][1][2] == "z.txt"

def test_extract_sorting_invalid_option_fallback_to_path(tmp_path):
    data = [
        {"path": "z.txt", "content": "z", "size_bytes": 1},
        {"path": "a.txt", "content": "a", "size_bytes": 1}
    ]
    content = json.dumps(data)

    stats = extract_files(content, tmp_path, dry_run=True, sort_by='invalid_option')

    assert stats['top_files'][0][2] == "a.txt"
    assert stats['top_files'][1][2] == "z.txt"

def test_extract_approx_tokens_xml_flag(tmp_path):
    content = """
<repository>
<file path="test.py" tokens="~5" size="14 B" lines="1">
print('hello')
</file>
</repository>
    """

    stats = extract_files(content, tmp_path, dry_run=True)

    assert stats['total_tokens'] == 5
    assert stats['token_count_is_approx'] is True

def test_extract_approx_tokens_json_flag(tmp_path):
    data = [
        {
            "path": "test.py",
            "content": "print('hello')",
            "tokens": 5,
            "tokens_is_approx": True,
            "size_bytes": 14
        }
    ]
    content = json.dumps(data)

    stats = extract_files(content, tmp_path, dry_run=True)

    assert stats['total_tokens'] == 5
    assert stats['token_count_is_approx'] is True

def test_extract_discovery_order_preserved_when_no_sorting_applied(tmp_path):
    data = [
        {"path": "b.txt", "content": "b"},
        {"path": "a.txt", "content": "a"}
    ]
    content = json.dumps(data)

    stats = extract_files(content, tmp_path, dry_run=True, sort_by='name', sort_reverse=False)

    assert stats['top_files'][0][2] == "b.txt"
    assert stats['top_files'][1][2] == "a.txt"
