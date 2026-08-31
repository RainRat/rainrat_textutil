import json
import pytest
from unittest.mock import patch
import sourcecombine


def test_print_presets_text(capsys):
    sourcecombine.print_presets()
    captured = capsys.readouterr()
    assert "BUILT-IN PRESETS" in captured.out
    assert "ai" in captured.out
    assert "analyze" in captured.out
    assert "Total: 2 built-in presets supported." in captured.out


def test_print_presets_filter_matching(capsys):
    sourcecombine.print_presets(query="analyze")
    captured = capsys.readouterr()
    assert "FILTERED BY 'analyze'" in captured.out
    assert "analyze" in captured.out
    assert "ai" not in captured.out
    assert "Matching: 1 built-in presets supported." in captured.out


def test_print_presets_filter_no_matches(capsys):
    sourcecombine.print_presets(query="unknown_query_xyz")
    captured = capsys.readouterr()
    assert "No presets matched the filter query 'unknown_query_xyz'" in captured.out
    assert "Matching: 0 built-in presets supported." in captured.out


def test_print_presets_json(capsys):
    sourcecombine.print_presets(json_format=True)
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["total"] == 2
    assert "ai" in data["presets"]
    assert "analyze" in data["presets"]
    assert "--ai, -a" in data["presets"]["ai"]["flag"]


def test_print_presets_json_with_query(capsys):
    sourcecombine.print_presets(query="ai", json_format=True)
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["total"] == 1
    assert "ai" in data["presets"]
    assert "analyze" not in data["presets"]


def test_cli_list_presets_main(capsys):
    with patch("sys.argv", ["sourcecombine", "--list-presets"]):
        with pytest.raises(SystemExit) as exc:
            sourcecombine.main()
        assert exc.value.code == 0
    captured = capsys.readouterr()
    assert "BUILT-IN PRESETS" in captured.out
    assert "ai" in captured.out


def test_cli_list_pre_alias_main(capsys):
    with patch("sys.argv", ["sourcecombine", "--list-pre"]):
        with pytest.raises(SystemExit) as exc:
            sourcecombine.main()
        assert exc.value.code == 0
    captured = capsys.readouterr()
    assert "BUILT-IN PRESETS" in captured.out


def test_cli_list_presets_json_main(capsys):
    with patch("sys.argv", ["sourcecombine", "--list-presets", "--json"]):
        with pytest.raises(SystemExit) as exc:
            sourcecombine.main()
        assert exc.value.code == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["total"] == 2
