import sourcecombine
from utils import DEFAULT_CONFIG

def test_total_size_limit(tmp_path, capsys):
    # Create some test files
    f1 = tmp_path / "file1.txt"
    f1.write_text("Hello World") # 11 bytes

    f2 = tmp_path / "file2.txt"
    f2.write_text("This is a second file") # 21 bytes

    f3 = tmp_path / "file3.txt"
    f3.write_text("Third file content") # 18 bytes

    output_file = tmp_path / "combined.txt"

    # Configure with a small size limit
    # Fixed overhead (default header/footer) is around:
    # "--- file1.txt ---" (17 bytes) + "\n" + "\n--- end file1.txt ---\n" (21 bytes) = 38 bytes per file
    # Total for file1: 38 + 11 = 49 bytes

    config = sourcecombine.copy.deepcopy(DEFAULT_CONFIG)
    config['search']['root_folders'] = [str(tmp_path)]
    config['filters']['max_total_size_bytes'] = 60 # Should allow file1 but not file2
    config['output']['file'] = str(output_file)

    stats = sourcecombine.find_and_combine_files(config, str(output_file))

    assert stats['total_files'] == 1
    assert stats['size_limit_reached'] is True
    assert stats['filter_reasons']['size_limit'] == 2

    content = output_file.read_text()
    assert "file1.txt" in content
    assert "file2.txt" not in content
    assert "file3.txt" not in content

def test_total_size_limit_cli_parsing(tmp_path, monkeypatch):
    import sys

    f1 = tmp_path / "file1.txt"
    f1.write_text("A" * 1000)

    # Test valid CLI parsing
    args = ["sourcecombine.py", str(tmp_path), "--max-total-size", "500B", "-o", str(tmp_path / "out.txt")]
    monkeypatch.setattr(sys, "argv", args)

    # We don't want to actually run the whole main here as it might exit
    # Instead let's test the logic in main that parses it

    parser = sourcecombine.argparse.ArgumentParser()
    # Mocking what main does
    filtering_group = parser.add_argument_group("Filtering & Selection")
    filtering_group.add_argument("--max-total-size")

    parsed_args = parser.parse_args(["--max-total-size", "1KB"])
    assert parsed_args.max_total_size == "1KB"

    import utils
    val = utils.parse_size_value(parsed_args.max_total_size)
    assert val == 1024

def test_summary_shows_size_limit(tmp_path, capsys):
    stats = {
        'total_files': 1,
        'total_discovered': 3,
        'total_size_bytes': 100,
        'total_tokens': 25,
        'total_lines': 5,
        'max_total_size_bytes': 200,
        'size_limit_reached': True,
        'filter_reasons': {'size_limit': 2},
        'files_by_extension': {'.txt': 1},
        'top_files': [(25, 100, 'file1.txt')]
    }

    class MockArgs:
        dry_run = False
        estimate_tokens = False
        list_files = False
        tree = False

    sourcecombine._print_execution_summary(stats, MockArgs(), pairing_enabled=False)

    captured = capsys.readouterr().err
    assert "WARNING: Output truncated due to total size limit." in captured
    assert "Size Limit Usage:" in captured
    assert "[#####-----]" in captured # 50% usage
