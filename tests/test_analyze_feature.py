import sys
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest
from sourcecombine import main

@pytest.fixture
def temp_project(tmp_path):
    """Create a temporary project structure for testing."""
    project_dir = tmp_path / "test_analyze_project"
    project_dir.mkdir()
    src_dir = project_dir / "src"
    src_dir.mkdir()

    (src_dir / "main.py").write_text("print('hello')", encoding='utf-8')
    (src_dir / "utils.py").write_text("def add(a, b): return a + b", encoding='utf-8')

    return project_dir

def test_analyze_flag_presets(temp_project, capsys, monkeypatch):
    """Verify that --analyze enables the correct preset flags."""
    monkeypatch.chdir(temp_project)

    # We'll mock find_and_combine_files to check the config it receives
    with patch('sourcecombine.find_and_combine_files') as mock_combine:
        mock_combine.return_value = {'total_files': 2}

        # Simulate: python sourcecombine.py --analyze
        monkeypatch.setattr(sys, 'argv', ['sourcecombine.py', '--analyze'])

        try:
            main()
        except SystemExit:
            pass

        # Check if find_and_combine_files was called with the expected arguments
        # args[0] is config, args[1] is output_path
        args, kwargs = mock_combine.call_args

        config = args[0]
        output_path = args[1]

        # Preset values based on --analyze logic:
        # args.dry_run = True
        # args.estimate_tokens = True
        # args.overview = True
        # args.include_tree = True
        # args.tree = True

        assert kwargs['dry_run'] is True
        assert kwargs['estimate_tokens'] is True
        assert kwargs['tree_view'] is True
        assert config['output']['project_overview'] is True
        assert config['output']['include_tree'] is True

def test_analyze_output_content(temp_project, capsys, monkeypatch):
    """Verify the output of --analyze contains expected sections."""
    monkeypatch.chdir(temp_project)

    # Run the actual main function but capture output
    monkeypatch.setattr(sys, 'argv', ['sourcecombine.py', '--analyze'])
    monkeypatch.setenv("NO_COLOR", "1")

    try:
        main()
    except SystemExit:
        pass

    out, err = capsys.readouterr()
    combined_output = out + err

    # Expected components in analysis output:
    # 1. Tree View (due to args.tree = True)
    # 2. Summary with PREVIEW ONLY (due to args.dry_run = True)
    # 3. Token estimation metrics (due to args.estimate_tokens = True)

    assert "src/" in combined_output
    assert "main.py" in combined_output
    assert "utils.py" in combined_output

    assert "COMBINE PREVIEW" in combined_output
    assert "Total Tokens" in combined_output
    assert "Largest Files" in combined_output
    assert "PREVIEW ONLY" in combined_output

def test_analyze_no_file_written(temp_project, monkeypatch):
    """Verify that --analyze does not create the default output file."""
    monkeypatch.chdir(temp_project)

    default_output = temp_project / "combined_files.txt"
    if default_output.exists():
        default_output.unlink()

    monkeypatch.setattr(sys, 'argv', ['sourcecombine.py', '--analyze'])

    try:
        main()
    except SystemExit:
        pass

    assert not default_output.exists()
