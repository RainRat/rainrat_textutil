import sys
import pytest
from pathlib import Path
from sourcecombine import main

def test_cli_comma_separated_extensions(tmp_path, monkeypatch):
    src_dir = tmp_path / "src"
    src_dir.mkdir()

    file_py = src_dir / "main.py"
    file_py.write_text("print('hello')", encoding="utf-8")

    file_js = src_dir / "index.js"
    file_js.write_text("console.log('hello')", encoding="utf-8")

    file_ts = src_dir / "index.ts"
    file_ts.write_text("console.log('ts')", encoding="utf-8")

    out_file = tmp_path / "combined.txt"

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "sourcecombine.py",
            str(src_dir),
            "--ext",
            "js,ts",
            "-o",
            str(out_file),
        ],
    )

    main()

    assert out_file.exists()
    content = out_file.read_text(encoding="utf-8")
    assert "index.js" in content
    assert "index.ts" in content
    assert "main.py" not in content

def test_cli_comma_separated_exclude_extensions(tmp_path, monkeypatch):
    src_dir = tmp_path / "src"
    src_dir.mkdir()

    file_py = src_dir / "main.py"
    file_py.write_text("print('hello')", encoding="utf-8")

    file_log = src_dir / "app.log"
    file_log.write_text("some logs", encoding="utf-8")

    file_tmp = src_dir / "temp.tmp"
    file_tmp.write_text("temp", encoding="utf-8")

    out_file = tmp_path / "combined.txt"

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "sourcecombine.py",
            str(src_dir),
            "--exclude-ext",
            "log,tmp",
            "-o",
            str(out_file),
        ],
    )

    main()

    assert out_file.exists()
    content = out_file.read_text(encoding="utf-8")
    assert "main.py" in content
    assert "app.log" not in content
    assert "temp.tmp" not in content

def test_cli_comma_separated_languages(tmp_path, monkeypatch):
    src_dir = tmp_path / "src"
    src_dir.mkdir()

    file_py = src_dir / "main.py"
    file_py.write_text("print('hello')", encoding="utf-8")

    file_js = src_dir / "index.js"
    file_js.write_text("console.log('hello')", encoding="utf-8")

    file_rb = src_dir / "app.rb"
    file_rb.write_text("puts 'hello'", encoding="utf-8")

    out_file = tmp_path / "combined.txt"

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "sourcecombine.py",
            str(src_dir),
            "--lang",
            "python,javascript",
            "-o",
            str(out_file),
        ],
    )

    main()

    assert out_file.exists()
    content = out_file.read_text(encoding="utf-8")
    assert "main.py" in content
    assert "index.js" in content
    assert "app.rb" not in content

def test_cli_comma_separated_exclude_languages(tmp_path, monkeypatch):
    src_dir = tmp_path / "src"
    src_dir.mkdir()

    file_py = src_dir / "main.py"
    file_py.write_text("print('hello')", encoding="utf-8")

    file_html = src_dir / "index.html"
    file_html.write_text("<h1>hello</h1>", encoding="utf-8")

    file_css = src_dir / "style.css"
    file_css.write_text("body { color: red; }", encoding="utf-8")

    out_file = tmp_path / "combined.txt"

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "sourcecombine.py",
            str(src_dir),
            "--exclude-lang",
            "html,css",
            "-o",
            str(out_file),
        ],
    )

    main()

    assert out_file.exists()
    content = out_file.read_text(encoding="utf-8")
    assert "main.py" in content
    assert "index.html" not in content
    assert "style.css" not in content

def test_cli_comma_separated_exclude_files(tmp_path, monkeypatch):
    src_dir = tmp_path / "src"
    src_dir.mkdir()

    file_py = src_dir / "main.py"
    file_py.write_text("print('hello')", encoding="utf-8")

    file_log = src_dir / "app.log"
    file_log.write_text("some logs", encoding="utf-8")

    file_tmp = src_dir / "temp.tmp"
    file_tmp.write_text("temp", encoding="utf-8")

    out_file = tmp_path / "combined.txt"

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "sourcecombine.py",
            str(src_dir),
            "-x",
            "*.log,*.tmp",
            "-o",
            str(out_file),
        ],
    )

    main()

    assert out_file.exists()
    content = out_file.read_text(encoding="utf-8")
    assert "main.py" in content
    assert "app.log" not in content
    assert "temp.tmp" not in content

def test_cli_comma_separated_exclude_folders(tmp_path, monkeypatch):
    src_dir = tmp_path / "src"
    src_dir.mkdir()

    file_py = src_dir / "main.py"
    file_py.write_text("print('hello')", encoding="utf-8")

    build_dir = src_dir / "build"
    build_dir.mkdir()
    file_build = build_dir / "output.js"
    file_build.write_text("console.log('build')", encoding="utf-8")

    node_dir = src_dir / "node_modules"
    node_dir.mkdir()
    file_node = node_dir / "package.js"
    file_node.write_text("console.log('node')", encoding="utf-8")

    out_file = tmp_path / "combined.txt"

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "sourcecombine.py",
            str(src_dir),
            "-X",
            "build,node_modules",
            "-o",
            str(out_file),
        ],
    )

    main()

    assert out_file.exists()
    content = out_file.read_text(encoding="utf-8")
    assert "main.py" in content
    assert "build/output.js" not in content
    assert "node_modules/package.js" not in content

def test_cli_comma_separated_inclusions(tmp_path, monkeypatch):
    src_dir = tmp_path / "src"
    src_dir.mkdir()

    file_py = src_dir / "main.py"
    file_py.write_text("print('hello')", encoding="utf-8")

    file_js = src_dir / "index.js"
    file_js.write_text("console.log('hello')", encoding="utf-8")

    file_css = src_dir / "style.css"
    file_css.write_text("body { color: red; }", encoding="utf-8")

    out_file = tmp_path / "combined.txt"

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "sourcecombine.py",
            str(src_dir),
            "-i",
            "*.py,*.js",
            "-o",
            str(out_file),
        ],
    )

    main()

    assert out_file.exists()
    content = out_file.read_text(encoding="utf-8")
    assert "main.py" in content
    assert "index.js" in content
    assert "style.css" not in content

def test_cli_comma_separated_ignore_files(tmp_path, monkeypatch):
    src_dir = tmp_path / "src"
    src_dir.mkdir()

    file_py = src_dir / "main.py"
    file_py.write_text("print('hello')", encoding="utf-8")

    file_js = src_dir / "index.js"
    file_js.write_text("console.log('hello')", encoding="utf-8")

    ignore_one = tmp_path / "ignore1"
    ignore_one.write_text("*.js", encoding="utf-8")

    ignore_two = tmp_path / "ignore2"
    ignore_two.write_text("*.py", encoding="utf-8")

    out_file = tmp_path / "combined.txt"

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "sourcecombine.py",
            str(src_dir),
            "--ignore-file",
            f"{ignore_one},{ignore_two}",
            "-o",
            str(out_file),
        ],
    )

    main()

    assert out_file.exists()
    content = out_file.read_text(encoding="utf-8")
    assert "main.py" not in content
    assert "index.js" not in content
