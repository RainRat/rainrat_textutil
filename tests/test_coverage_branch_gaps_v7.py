import sys
import os
import json
import tempfile
from pathlib import Path

sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))

import utils
import sourcecombine


def test_get_project_identity_readme_empty_lines_branch():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        readme = tmp / "README.md"
        readme.write_text("# Project Title\n\n  \n\n")

        identity = utils.get_project_identity(tmp)
        assert identity["project_name"] == "Project Title"
        assert identity["project_description"] == ""


def test_pair_files_truncated_map_missing_header_branch():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        f1 = tmp / "src" / "main.cpp"
        f1.parent.mkdir(parents=True)
        f1.write_text("int main() { return 0; }")

        paired = sourcecombine._pair_files([f1], ["cpp"], ["h"], True, root_path=tmp)
        assert len(paired) == 1


def test_find_and_combine_files_empty_tree_content_branch():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        cfg = utils.DEFAULT_CONFIG.copy()
        cfg["search"] = {"root_folder": str(tmp), "ignore_files": []}
        cfg["output"] = {"include_tree": True}

        out_file = tmp / "output.txt"
        res = sourcecombine.find_and_combine_files(cfg, str(out_file))
        assert res is not None


def test_find_and_combine_files_global_footer_dry_run_branch():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        cfg = utils.DEFAULT_CONFIG.copy()
        cfg["search"] = {"root_folder": str(tmp), "ignore_files": []}
        cfg["output"] = {"global_footer_template": "FOOTER END"}

        out_file = tmp / "output.txt"
        res = sourcecombine.find_and_combine_files(
            cfg, str(out_file), dry_run=True, estimate_tokens=False
        )
        assert res is not None


def test_file_processor_emit_json_missing_modified_branch():
    fp = sourcecombine.FileProcessor({}, {}, output_format="json")

    class BufferWriter:
        def __init__(self):
            self.buf = ""

        def write(self, s):
            self.buf += s

    writer = BufferWriter()
    fp._emit_entry(writer, "file content", Path("file.py"), 12, 3, False, 1, modified=None)
    parsed = json.loads(writer.buf)
    assert "modified" not in parsed


def test_file_processor_write_max_size_placeholder_shebang_sampling():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        script = tmp / "script_no_ext"
        script.write_text("#!/usr/bin/env python\nprint('hello')\n")

        fp = sourcecombine.FileProcessor(
            {}, {"max_size_placeholder": "[OVERSIZED {{LANG}}]"}, output_format="text"
        )

        class BufferWriter:
            def __init__(self):
                self.buf = ""

            def write(self, s):
                self.buf += s

        writer = BufferWriter()
        fp.write_max_size_placeholder(script, tmp, writer)
        assert "python" in writer.buf.lower()


def test_print_extensions_query_filter():
    sourcecombine.print_extensions(query="python")


def test_print_presets_query_filter():
    sourcecombine.print_presets(query="review")
