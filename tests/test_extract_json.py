import json
from sourcecombine import extract_files, main


def test_extract_files_json_format_dry_run(tmp_path, capsys):
    content = json.dumps([
        {"path": "foo.py", "content": "print('hello')", "size": 14, "lines": 1, "tokens": 4},
        {"path": "bar.js", "content": "console.log('hi')", "size": 18, "lines": 1, "tokens": 5}
    ])
    sources = [("test.json", content)]
    out_dir = tmp_path / "output"

    extract_files(sources, out_dir, dry_run=True, json_format=True)

    captured = capsys.readouterr()
    report = json.loads(captured.out)

    assert report["title"] == "Extraction Report"
    assert report["dry_run"] is True
    assert report["output_folder"] == out_dir.as_posix()
    assert len(report["files"]) == 2
    assert report["files"][0]["status"] == "WOULD_EXTRACT"
    assert report["files"][0]["path"] == "foo.py"
    assert report["files"][0]["size"] == 14
    assert report["summary"]["extracted_count"] == 2
    assert report["summary"]["error_count"] == 0
    assert report["summary"]["total_discovered"] == 2
    assert not (out_dir / "foo.py").exists()


def test_extract_files_json_format_actual_extraction(tmp_path, capsys):
    content = json.dumps([
        {"path": "a.txt", "content": "Hello World", "size": 11, "lines": 1}
    ])
    sources = [("test.json", content)]
    out_dir = tmp_path / "extracted"

    extract_files(sources, out_dir, dry_run=False, json_format=True)

    captured = capsys.readouterr()
    report = json.loads(captured.out)

    assert report["title"] == "Extraction Report"
    assert report["dry_run"] is False
    assert len(report["files"]) == 1
    assert report["files"][0]["status"] == "EXTRACTED"
    assert report["files"][0]["path"] == "a.txt"
    assert report["summary"]["extracted_count"] == 1
    assert (out_dir / "a.txt").exists()
    assert (out_dir / "a.txt").read_text(encoding="utf-8") == "Hello World"


def test_extract_files_json_format_skipped_and_unsafe_paths(tmp_path, capsys):
    content = json.dumps([
        {"path": "valid.txt", "content": None},
        {"path": "/absolute/path.txt", "content": "bad"},
        {"path": "../relative/path.txt", "content": "bad"}
    ])
    sources = [("test.json", content)]
    out_dir = tmp_path / "extracted"

    extract_files(sources, out_dir, dry_run=False, json_format=True)

    captured = capsys.readouterr()
    report = json.loads(captured.out)

    assert report["summary"]["skipped_count"] == 3
    assert report["summary"]["extracted_count"] == 0
    statuses = [f["status"] for f in report["files"]]
    assert all(s == "SKIPPED" for s in statuses)


def test_extract_cli_json_flag(tmp_path, capsys, monkeypatch):
    json_file = tmp_path / "combined.json"
    json_file.write_text(json.dumps([
        {"path": "sample.py", "content": "x = 42"}
    ]), encoding="utf-8")
    out_dir = tmp_path / "cli_out"

    monkeypatch.setattr("sys.argv", [
        "sourcecombine.py",
        "--extract",
        str(json_file),
        "--output",
        str(out_dir),
        "--json",
        "--dry-run"
    ])

    try:
        main()
    except SystemExit as e:
        assert e.code == 0

    captured = capsys.readouterr()
    report = json.loads(captured.out)
    assert report["title"] == "Extraction Report"
    assert report["dry_run"] is True
    assert report["files"][0]["path"] == "sample.py"
    assert "Found 1 files to extract" not in captured.err


def test_extract_cli_json_clean_stderr(tmp_path):
    import subprocess
    json_file = tmp_path / "combined.json"
    json_file.write_text(json.dumps([
        {"path": "hello.txt", "content": "world"}
    ]), encoding="utf-8")
    out_dir = tmp_path / "out"

    res = subprocess.run([
        "python", "sourcecombine.py",
        "--extract", str(json_file),
        "--output", str(out_dir),
        "--json"
    ], capture_output=True, text=True, check=True)

    report = json.loads(res.stdout)
    assert report["summary"]["extracted_count"] == 1
    assert res.stderr.strip() == ""


def test_extract_files_json_format_strip_components(tmp_path, capsys):
    content = json.dumps([
        {"path": "foo/bar.txt", "content": "Hello", "size": None, "lines": None}
    ])
    sources = [("test.json", content)]
    out_dir = tmp_path / "extracted"

    extract_files(sources, out_dir, dry_run=False, json_format=True, strip_components=2)

    captured = capsys.readouterr()
    report = json.loads(captured.out)

    assert report["summary"]["skipped_count"] == 1
    assert report["files"][0]["status"] == "SKIPPED"
    assert "fewer than 2 components" in report["files"][0]["reason"]
    assert report["files"][0]["size"] == 5
    assert report["files"][0]["lines"] == 1


def test_extract_files_strip_components_non_json_logging(tmp_path, capsys, caplog):
    content = json.dumps([
        {"path": "single.txt", "content": "Test"}
    ])
    sources = [("test.json", content)]
    out_dir = tmp_path / "extracted"

    with caplog.at_level("WARNING"):
        extract_files(sources, out_dir, dry_run=False, json_format=False, strip_components=1)

    assert "Skipping path with fewer than 1 components: single.txt" in caplog.text


def test_extract_files_json_format_invalid_path_exception(tmp_path, capsys, monkeypatch):
    content = json.dumps([
        {"path": "some_file.txt", "content": "Hello"}
    ])
    sources = [("test.json", content)]
    out_dir = tmp_path / "extracted"

    def mock_resolve(*args, **kwargs):
        raise OSError("Invalid resolution error")

    monkeypatch.setattr("pathlib.Path.resolve", mock_resolve)

    extract_files(sources, out_dir, dry_run=False, json_format=True)

    captured = capsys.readouterr()
    report = json.loads(captured.out)

    assert report["summary"]["skipped_count"] == 1
    assert report["files"][0]["status"] == "SKIPPED"
    assert "Invalid path" in report["files"][0]["reason"]
    assert "Invalid resolution error" in report["files"][0]["error"]


def test_extract_files_json_format_write_os_error(tmp_path, capsys, monkeypatch):
    content = json.dumps([
        {"path": "error.txt", "content": "Sample content"}
    ])
    sources = [("test.json", content)]
    out_dir = tmp_path / "extracted"

    def mock_write_text(*args, **kwargs):
        raise OSError("Permission denied / disk full")

    monkeypatch.setattr("pathlib.Path.write_text", mock_write_text)

    extract_files(sources, out_dir, dry_run=False, json_format=True)

    captured = capsys.readouterr()
    report = json.loads(captured.out)

    assert report["summary"]["error_count"] == 1
    assert report["files"][0]["status"] == "ERROR"
    assert "Permission denied / disk full" in report["files"][0]["error"]


def test_extract_files_json_format_fallback_size_and_lines_computation(tmp_path, capsys):
    content = json.dumps([
        {"path": "fallback.py", "content": "print('line 1')\nprint('line 2')\n"}
    ])
    sources = [("test.json", content)]
    out_dir = tmp_path / "out"

    extract_files(sources, out_dir, dry_run=True, json_format=True)

    captured = capsys.readouterr()
    report = json.loads(captured.out)

    assert report["files"][0]["size"] == 32
    assert report["files"][0]["lines"] == 2
