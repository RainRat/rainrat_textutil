import json
import logging
import pytest
import utils
import sourcecombine


def test_import_ignore_patterns_none_inputs():
    assert sourcecombine.import_ignore_patterns(None, None) is None
    cfg = utils.DEFAULT_CONFIG.copy()
    assert sourcecombine.import_ignore_patterns(None, cfg) == cfg


def test_import_ignore_patterns_text_file(tmp_path):
    ignore_file = tmp_path / "custom_ignore.txt"
    ignore_file.write_text(
        "# Comment line\n"
        "*.tmp\n"
        "  \n"
        "  *.log  \n"
        "# Another comment\n"
        "build_output/\n",
        encoding="utf-8"
    )

    config = copy_config()
    result = sourcecombine.import_ignore_patterns(ignore_file, config)

    fn_ex = result["filters"]["exclusions"]["filenames"]
    assert "*.tmp" in fn_ex
    assert "*.log" in fn_ex
    assert "build_output/" in fn_ex


def test_import_ignore_patterns_json_array(tmp_path):
    json_file = tmp_path / "ignore.json"
    json_file.write_text(json.dumps(["*.bak", "cache/"]), encoding="utf-8")

    config = copy_config()
    result = sourcecombine.import_ignore_patterns(json_file, config)

    fn_ex = result["filters"]["exclusions"]["filenames"]
    assert "*.bak" in fn_ex
    assert "cache/" in fn_ex


def test_import_ignore_patterns_json_object_variants(tmp_path):
    # Test 'patterns' key
    f1 = tmp_path / "f1.json"
    f1.write_text(json.dumps({"patterns": ["*.pat1"]}), encoding="utf-8")
    cfg1 = sourcecombine.import_ignore_patterns(f1, copy_config())
    assert "*.pat1" in cfg1["filters"]["exclusions"]["filenames"]

    # Test 'exclusions.filenames' structure
    f2 = tmp_path / "f2.json"
    f2.write_text(json.dumps({"exclusions": {"filenames": ["*.pat2"]}}), encoding="utf-8")
    cfg2 = sourcecombine.import_ignore_patterns(f2, copy_config())
    assert "*.pat2" in cfg2["filters"]["exclusions"]["filenames"]

    # Test 'filenames' key
    f3 = tmp_path / "f3.json"
    f3.write_text(json.dumps({"filenames": ["*.pat3"]}), encoding="utf-8")
    cfg3 = sourcecombine.import_ignore_patterns(f3, copy_config())
    assert "*.pat3" in cfg3["filters"]["exclusions"]["filenames"]

    # Test 'categories' key (exported format)
    f4 = tmp_path / "f4.json"
    f4.write_text(json.dumps({"categories": {"Group A": ["*.pat4"], "Group B": ["*.pat5"]}}), encoding="utf-8")
    cfg4 = sourcecombine.import_ignore_patterns(f4, copy_config())
    assert "*.pat4" in cfg4["filters"]["exclusions"]["filenames"]
    assert "*.pat5" in cfg4["filters"]["exclusions"]["filenames"]


def test_import_ignore_patterns_yaml_file(tmp_path):
    if not utils.yaml:
        pytest.skip("PyYAML not installed")

    yaml_file = tmp_path / "ignore.yml"
    yaml_file.write_text(
        "patterns:\n"
        "  - '*.yaml_tmp'\n"
        "  - 'temp_folder/'\n",
        encoding="utf-8"
    )

    config = copy_config()
    result = sourcecombine.import_ignore_patterns(yaml_file, config)

    fn_ex = result["filters"]["exclusions"]["filenames"]
    assert "*.yaml_tmp" in fn_ex
    assert "temp_folder/" in fn_ex


def test_import_ignore_patterns_stdin(monkeypatch):
    input_text = "# comment\nstdin_pattern_*.tmp\n"
    monkeypatch.setattr("sys.stdin", pytest.importorskip("io").StringIO(input_text))

    config = copy_config()
    result = sourcecombine.import_ignore_patterns("-", config)

    fn_ex = result["filters"]["exclusions"]["filenames"]
    assert "stdin_pattern_*.tmp" in fn_ex


def test_import_ignore_patterns_missing_file():
    config = copy_config()
    with pytest.raises(SystemExit):
        sourcecombine.import_ignore_patterns("non_existent_ignore_file_12345.txt", config)


def test_import_ignore_patterns_empty_file(tmp_path, caplog):
    empty_file = tmp_path / "empty.txt"
    empty_file.write_text("   \n # only comment\n", encoding="utf-8")

    config = copy_config()
    with caplog.at_level(logging.WARNING):
        result = sourcecombine.import_ignore_patterns(empty_file, config)

    assert "no patterns imported" in caplog.text


def test_import_ignore_patterns_empty_json_list(tmp_path, caplog):
    empty_json = tmp_path / "empty.json"
    empty_json.write_text("[]", encoding="utf-8")

    config = copy_config()
    with caplog.at_level(logging.WARNING):
        result = sourcecombine.import_ignore_patterns(empty_json, config)

    assert "no patterns imported" in caplog.text
    assert "[]" not in result["filters"]["exclusions"]["filenames"]


def test_import_ignore_patterns_invalid_pattern_type(tmp_path):
    json_file = tmp_path / "invalid.json"
    json_file.write_text(json.dumps([123, 456]), encoding="utf-8")

    config = copy_config()
    with pytest.raises(SystemExit):
        sourcecombine.import_ignore_patterns(json_file, config)


def test_import_ignore_cli_list_ignores(tmp_path, monkeypatch, capsys):
    ignore_file = tmp_path / "cli_rules.txt"
    ignore_file.write_text("imported_cli_pattern_*.log\n", encoding="utf-8")

    monkeypatch.setattr(
        "sys.argv",
        ["sourcecombine.py", "--import-ignore", str(ignore_file), "--list-ignores"]
    )

    with pytest.raises(SystemExit) as exc_info:
        sourcecombine.main()

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "imported_cli_pattern_*.log" in captured.out


def test_import_ignore_cli_filtering(tmp_path, monkeypatch):
    src_dir = tmp_path / "src"
    src_dir.mkdir()

    f1 = src_dir / "keep.py"
    f1.write_text("print('hello')", encoding="utf-8")

    f2 = src_dir / "skip_me.tmp"
    f2.write_text("skip this", encoding="utf-8")

    rules_file = tmp_path / "rules.json"
    rules_file.write_text(json.dumps(["*.tmp"]), encoding="utf-8")

    out_file = tmp_path / "combined.txt"

    monkeypatch.setattr(
        "sys.argv",
        [
            "sourcecombine.py",
            str(src_dir),
            "--import-ig", str(rules_file),
            "--output", str(out_file)
        ]
    )

    sourcecombine.main()

    content = out_file.read_text(encoding="utf-8")
    assert "keep.py" in content
    assert "skip_me.tmp" not in content


def copy_config():
    import copy
    return copy.deepcopy(utils.DEFAULT_CONFIG)
