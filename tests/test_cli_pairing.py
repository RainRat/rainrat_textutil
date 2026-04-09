import subprocess
import pytest

@pytest.fixture
def test_env(tmp_path):
    """Create a temporary project structure for testing pairing."""
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    # Create some source/header pairs
    (project_dir / "main.cpp").write_text("int main() { return 0; }")
    (project_dir / "main.h").write_text("int main();")

    (project_dir / "utils.cpp").write_text("void util() {}")
    (project_dir / "utils.h").write_text("void util();")

    # Create an unpaired file
    (project_dir / "readme.txt").write_text("Just a readme.")

    return project_dir

def test_cli_pairing_basic(test_env, tmp_path):
    """Test basic pairing via CLI."""
    output_dir = tmp_path / "output"

    # Run sourcecombine with --pair
    result = subprocess.run(
        [
            "python3", "sourcecombine.py",
            str(test_env),
            "--output", str(output_dir),
            "--pair", ".cpp", ".h"
        ],
        capture_output=True,
        text=True
    )

    assert result.returncode == 0

    # Check that paired files were created
    assert (output_dir / "main.combined").exists()
    assert (output_dir / "utils.combined").exists()

    # Check that unpaired file was NOT created
    assert not (output_dir / "readme.txt.combined").exists()
    assert not (output_dir / "readme.txt").exists()

    # Verify content of one paired file
    content = (output_dir / "main.combined").read_text()
    assert "main.cpp" in content
    assert "main.h" in content
    assert "int main() { return 0; }" in content
    assert "int main();" in content

def test_cli_pairing_include_unpaired(test_env, tmp_path):
    """Test pairing with --include-unpaired via CLI."""
    output_dir = tmp_path / "output"

    # Run sourcecombine with --pair and --include-unpaired
    result = subprocess.run(
        [
            "python3", "sourcecombine.py",
            str(test_env),
            "--output", str(output_dir),
            "--pair", ".cpp", ".h",
            "--include-unpaired"
        ],
        capture_output=True,
        text=True
    )

    assert result.returncode == 0

    # Check that paired files AND unpaired file were created
    assert (output_dir / "main.combined").exists()
    assert (output_dir / "utils.combined").exists()
    assert (output_dir / "readme.txt").exists()

def test_cli_pairing_custom_template(test_env, tmp_path):
    """Test pairing with --pair-template via CLI."""
    output_dir = tmp_path / "output"

    # Run sourcecombine with --pair and --pair-template
    result = subprocess.run(
        [
            "python3", "sourcecombine.py",
            str(test_env),
            "--output", str(output_dir),
            "--pair", ".cpp", ".h",
            "--pair-template", "{{STEM}}.out"
        ],
        capture_output=True,
        text=True
    )

    assert result.returncode == 0

    # Check that paired files were created with the custom extension
    assert (output_dir / "main.out").exists()
    assert (output_dir / "utils.out").exists()

def test_cli_pairing_normalized_extensions(test_env, tmp_path):
    """Test that extensions without leading dots are handled correctly."""
    output_dir = tmp_path / "output"

    # Run sourcecombine with --pair using extensions without dots
    result = subprocess.run(
        [
            "python3", "sourcecombine.py",
            str(test_env),
            "--output", str(output_dir),
            "--pair", "cpp", "h"
        ],
        capture_output=True,
        text=True
    )

    assert result.returncode == 0

    assert (output_dir / "main.combined").exists()
    assert (output_dir / "utils.combined").exists()
