import json
import pytest
import sourcecombine
import utils


def test_import_replacements_oserror(tmp_path, monkeypatch):
    rules_file = tmp_path / "rules.json"
    rules_file.write_text('{"regex_replacements": []}', encoding="utf-8")

    orig_open = open

    def fake_open(file, *args, **kwargs):
        if str(file) == str(rules_file):
            raise OSError("Simulated disk error")
        return orig_open(file, *args, **kwargs)

    monkeypatch.setattr("builtins.open", fake_open)

    with pytest.raises(SystemExit) as exc:
        sourcecombine.import_replacements(str(rules_file), {})
    assert exc.value.code == 1


def test_import_replacements_no_yaml_json_error(tmp_path, monkeypatch):
    rules_file = tmp_path / "rules.txt"
    rules_file.write_text("invalid json content", encoding="utf-8")

    monkeypatch.setattr(utils, "yaml", None)

    with pytest.raises(SystemExit) as exc:
        sourcecombine.import_replacements(str(rules_file), {})
    assert exc.value.code == 1


def test_import_replacements_normalize_rule_edge_cases(tmp_path):
    rules_file = tmp_path / "rules.json"
    rules_file.write_text(json.dumps([123, {"foo": "bar"}]), encoding="utf-8")

    config = {}
    res = sourcecombine.import_replacements(str(rules_file), config)
    assert res["processing"]["regex_replacements"] == []


def test_import_replacements_none_processing_and_rule_keys(tmp_path):
    rules_file = tmp_path / "rules.json"
    rules_file.write_text(json.dumps([{"pattern": "a", "replacement": "b"}]), encoding="utf-8")

    config = {"processing": None}
    res = sourcecombine.import_replacements(str(rules_file), config)
    assert len(res["processing"]["regex_replacements"]) == 1

    config2 = {"processing": {"regex_replacements": None, "line_regex_replacements": None}}
    res2 = sourcecombine.import_replacements(str(rules_file), config2)
    assert len(res2["processing"]["regex_replacements"]) == 1


def test_main_list_replacements_with_import_replacements(tmp_path, monkeypatch, capsys):
    rules_file = tmp_path / "rules.json"
    rules_file.write_text(json.dumps([{"pattern": "foo", "replacement": "bar"}]), encoding="utf-8")
    target_dir = tmp_path / "target"
    target_dir.mkdir()

    monkeypatch.setattr("sys.argv", ["sourcecombine.py", "--list-replacements", "--import-replacements", str(rules_file), str(target_dir)])

    with pytest.raises(SystemExit) as exc:
        sourcecombine.main()
    assert exc.value.code == 0
    captured = capsys.readouterr()
    assert "[Text Replacements (--replace)]" in captured.out


def test_update_identity_from_dict_non_dict():
    identity = {"project_name": "initial"}
    utils._update_identity_from_dict("not_a_dict", identity)
    assert identity["project_name"] == "initial"
