import os
import shutil
from pathlib import Path
from utils import get_project_identity

def test_get_project_identity_cmake(tmp_path):
    cmake_file = tmp_path / "CMakeLists.txt"
    cmake_file.write_text('project(MyCmakeProj VERSION 2.1.0 DESCRIPTION "A CMake Project")', encoding='utf-8')

    identity = get_project_identity(tmp_path)
    assert identity["project_name"] == "MyCmakeProj"
    assert identity["project_version"] == "2.1.0"
    assert identity["project_description"] == "A CMake Project"

def test_get_project_identity_cmake_multiline(tmp_path):
    cmake_file = tmp_path / "CMakeLists.txt"
    cmake_file.write_text('''
        project(
            MyCmakeProj
            VERSION 3.0
            DESCRIPTION "Multi-line description"
        )
    ''', encoding='utf-8')

    identity = get_project_identity(tmp_path)
    assert identity["project_name"] == "MyCmakeProj"
    assert identity["project_version"] == "3.0"
    assert identity["project_description"] == "Multi-line description"

def test_get_project_identity_julia(tmp_path):
    julia_file = tmp_path / "Project.toml"
    julia_file.write_text('name = "MyJuliaPkg"\nversion = "0.5.0"', encoding='utf-8')

    identity = get_project_identity(tmp_path)
    assert identity["project_name"] == "MyJuliaPkg"
    assert identity["project_version"] == "0.5.0"

def test_get_project_identity_julia_quoted(tmp_path):
    julia_file = tmp_path / "Project.toml"
    julia_file.write_text("name = 'QuotedPkg'\nversion = '1.2.3'", encoding='utf-8')

    identity = get_project_identity(tmp_path)
    assert identity["project_name"] == "QuotedPkg"
    assert identity["project_version"] == "1.2.3"
