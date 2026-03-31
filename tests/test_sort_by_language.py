import os
import pytest
import copy
from pathlib import Path
from sourcecombine import find_and_combine_files, extract_files
import utils

def test_sort_by_language(tmp_path):
    # Setup test files with different languages
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    # Python files (lang: python)
    (project_dir / "z.py").write_text("print('z')", encoding='utf-8')
    (project_dir / "a.py").write_text("print('a')", encoding='utf-8')

    # C++ files (lang: cpp)
    (project_dir / "m.cpp").write_text("int main() { return 0; }", encoding='utf-8')

    # Bash files (lang: bash)
    sh_file = project_dir / "script.sh"
    sh_file.write_text("#!/bin/bash\necho 1", encoding='utf-8')

    config = copy.deepcopy(utils.DEFAULT_CONFIG)
    utils.validate_config(config)
    config['search']['root_folders'] = [str(project_dir)]
    config['output']['sort_by'] = 'language'
    config['output']['file'] = str(tmp_path / "combined.txt")

    # 'bash' < 'cpp' < 'python'
    # Expected order: script.sh, m.cpp, a.py, z.py

    stats = find_and_combine_files(config, config['output']['file'])

    combined_content = Path(config['output']['file']).read_text(encoding='utf-8')

    # Check the order of files in the combined content
    # We look for the headers
    indices = [
        combined_content.find("script.sh"),
        combined_content.find("m.cpp"),
        combined_content.find("a.py"),
        combined_content.find("z.py")
    ]

    assert all(i != -1 for i in indices)
    assert indices == sorted(indices), f"Files not sorted by language correctly: {indices}"

def test_sort_by_language_reverse(tmp_path):
    # Setup test files
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    (project_dir / "a.py").write_text("print('a')", encoding='utf-8') # python
    (project_dir / "m.cpp").write_text("int main() { return 0; }", encoding='utf-8') # cpp

    config = copy.deepcopy(utils.DEFAULT_CONFIG)
    utils.validate_config(config)
    config['search']['root_folders'] = [str(project_dir)]
    config['output']['sort_by'] = 'language'
    config['output']['sort_reverse'] = True
    config['output']['file'] = str(tmp_path / "combined_rev.txt")

    # Expected order: a.py (python), m.cpp (cpp)

    find_and_combine_files(config, config['output']['file'])
    combined_content = Path(config['output']['file']).read_text(encoding='utf-8')

    pos_py = combined_content.find("a.py")
    pos_cpp = combined_content.find("m.cpp")

    assert pos_py < pos_cpp

def test_sort_by_language_paired(tmp_path):
    # Setup test files
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    out_dir = tmp_path / "out"
    out_dir.mkdir()

    # python file
    (project_dir / "main.py").write_text("print(1)", encoding='utf-8')

    # cpp pair
    (project_dir / "util.cpp").write_text("int f() { return 1; }", encoding='utf-8')
    (project_dir / "util.h").write_text("int f();", encoding='utf-8')

    config = copy.deepcopy(utils.DEFAULT_CONFIG)
    utils.validate_config(config)
    config['search']['root_folders'] = [str(project_dir)]
    config['pairing']['enabled'] = True
    config['pairing']['include_mismatched'] = True
    config['pairing']['source_extensions'] = ['.py', '.cpp']
    config['pairing']['header_extensions'] = ['.h']
    config['output']['sort_by'] = 'language'
    config['output']['folder'] = str(out_dir)

    # cpp < python
    # Expected order of processing: util, main

    stats = find_and_combine_files(config, config['output']['folder'])

    file_names = [Path(f[2]).name for f in stats['top_files']]

    assert "util.cpp" in file_names
    assert "util.h" in file_names
    assert "main.py" in file_names

    # Find indices
    idx_util_cpp = file_names.index("util.cpp")
    idx_main_py = file_names.index("main.py")

    assert idx_util_cpp < idx_main_py

def test_extract_sort_by_language(tmp_path):
    combined_file = tmp_path / "combined.json"
    combined_file.write_text(r'[{"path": "a.py", "content": "print(1)"}, {"path": "b.cpp", "content": "int main() {}"}]', encoding='utf-8')

    out_dir = tmp_path / "extracted"
    out_dir.mkdir()

    # b.cpp (cpp) < a.py (python)

    stats = extract_files(
        [(str(combined_file), combined_file.read_text())],
        str(out_dir),
        sort_by='language'
    )

    file_names = [f[2] for f in stats['top_files']]
    assert file_names == ["b.cpp", "a.py"]

def test_sort_by_language_custom_map(tmp_path):
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    (project_dir / "file.xyz").write_text("content", encoding='utf-8') # lang will be xyz or text
    (project_dir / "main.py").write_text("print(1)", encoding='utf-8') # lang: python

    config = copy.deepcopy(utils.DEFAULT_CONFIG)
    utils.validate_config(config)
    config['search']['root_folders'] = [str(project_dir)]
    config['search']['custom_languages'] = {".xyz": "aaa_lang"} # aaa_lang < python
    config['output']['sort_by'] = 'language'
    config['output']['file'] = str(tmp_path / "combined_custom.txt")

    find_and_combine_files(config, config['output']['file'])
    combined_content = Path(config['output']['file']).read_text(encoding='utf-8')

    pos_xyz = combined_content.find("file.xyz")
    pos_py = combined_content.find("main.py")

    assert pos_xyz != -1
    assert pos_py != -1
    assert pos_xyz < pos_py
