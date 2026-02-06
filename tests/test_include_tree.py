import copy
import pytest
from pathlib import Path
from sourcecombine import find_and_combine_files, _generate_tree_string
from utils import DEFAULT_CONFIG

@pytest.fixture
def tree_config(tmp_path):
    config = copy.deepcopy(DEFAULT_CONFIG)
    config['search'] = {'root_folders': [str(tmp_path)]}
    config['output']['include_tree'] = True
    config['output']['file'] = str(tmp_path / "output.txt")
    return config

def test_generate_tree_string_text():
    root = Path("/root")
    paths = [
        root / "README.md",
        root / "src" / "main.py",
        root / "src" / "utils.py",
    ]

    result = _generate_tree_string(paths, root, 'text')
    assert "Project Structure:" in result
    assert "root/" in result
    assert "├── README.md" in result
    assert "└── src" in result
    assert "    ├── main.py" in result
    assert "    └── utils.py" in result
    assert "-" * 20 in result

def test_generate_tree_string_markdown():
    root = Path("/root")
    paths = [
        root / "main.py",
    ]

    result = _generate_tree_string(paths, root, 'markdown')
    assert "## Project Structure" in result
    assert "```text" in result
    assert "root/" in result
    assert "└── main.py" in result
    assert "```" in result

def test_tree_integration_text(tmp_path, tree_config):
    # Setup files
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "a.txt").write_text("content a")
    (tmp_path / "b.txt").write_text("content b")

    output_file = tmp_path.parent / "output_text.txt"
    find_and_combine_files(tree_config, str(output_file))

    content = output_file.read_text(encoding='utf-8')

    assert "Project Structure:" in content
    assert f"{tmp_path.name}/" in content
    assert "├── b.txt" in content
    assert "└── src" in content
    assert "    └── a.txt" in content
    assert "content a" in content
    assert "content b" in content

def test_tree_integration_markdown(tmp_path, tree_config):
    # Setup files
    (tmp_path / "doc.md").write_text("# Doc")

    output_file = tmp_path.parent / "output_md.md"
    find_and_combine_files(tree_config, str(output_file), output_format='markdown')

    content = output_file.read_text(encoding='utf-8')

    assert "## Project Structure" in content
    assert "```text" in content
    assert f"{tmp_path.name}/" in content
    assert "└── doc.md" in content
    assert "```" in content
    assert "# Doc" in content

def test_tree_estimate_tokens(tmp_path, tree_config):
    (tmp_path / "a.txt").write_text("content a")

    stats_with_tree = find_and_combine_files(tree_config, None, estimate_tokens=True)

    tree_config['output']['include_tree'] = False
    stats_without_tree = find_and_combine_files(tree_config, None, estimate_tokens=True)

    # Tree adds tokens
    assert stats_with_tree['total_tokens'] > stats_without_tree['total_tokens']
