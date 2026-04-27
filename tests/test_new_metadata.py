import json
from pathlib import Path
import sourcecombine
import utils

def test_get_project_name_package_json(tmp_path):
    pkg_json = tmp_path / "package.json"
    pkg_json.write_text(json.dumps({"name": "test-pkg"}), encoding='utf-8')
    assert utils.get_project_name(tmp_path) == "test-pkg"

def test_get_project_name_pyproject_toml_top(tmp_path):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('name = "test-pyproject"', encoding='utf-8')
    assert utils.get_project_name(tmp_path) == "test-pyproject"

def test_get_project_name_pyproject_toml_project_section(tmp_path):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "test-section"', encoding='utf-8')
    assert utils.get_project_name(tmp_path) == "test-section"

def test_get_project_name_fallback_folder(tmp_path):
    folder = tmp_path / "my-awesome-project"
    folder.mkdir()
    assert utils.get_project_name(folder) == "my-awesome-project"

def test_datetime_placeholders():
    placeholders = utils.get_datetime_placeholders()
    assert "date" in placeholders
    assert "time" in placeholders
    assert "datetime" in placeholders
    # Basic format check (YYYY-MM-DD)
    import re
    assert re.match(r"\d{4}-\d{2}-\d{2}", placeholders["date"])

def test_template_rendering_with_new_placeholders():
    stats = {
        'project_name': 'MyProject',
        'date': '2025-01-01',
        'time': '12:00:00',
        'datetime': '2025-01-01 12:00:00',
        'total_files': 1,
        'total_size_bytes': 100,
        'total_tokens': 10,
        'total_lines': 5
    }

    template = "Project: {{PROJECT_NAME}}, Date: {{DATE}}, Time: {{TIME}}, DT: {{DATETIME}}"
    rendered = sourcecombine._render_global_template(template, stats)
    assert rendered == "Project: MyProject, Date: 2025-01-01, Time: 12:00:00, DT: 2025-01-01 12:00:00"

    # Test individual file template
    file_template = "File in {{PROJECT_NAME}} at {{DATE}}"
    from pathlib import Path
    rendered_file = sourcecombine._render_template(file_template, Path("test.py"), git_info=stats)
    assert rendered_file == "File in MyProject at 2025-01-01"
