import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import sourcecombine
from utils import get_project_identity


def test_progress_bar_tqdm_import_success():
    mock_tqdm_module = MagicMock()
    mock_tqdm_class = MagicMock()
    mock_tqdm_module.tqdm = mock_tqdm_class

    with patch.dict(sys.modules, {"tqdm": mock_tqdm_module}):
        result = sourcecombine._progress_bar([1, 2, 3], enabled=True, desc="Testing")
        assert result == mock_tqdm_class.return_value
        mock_tqdm_class.assert_called_once_with([1, 2, 3], desc="Testing")


def test_get_project_identity_readme_setext_header_description(tmp_path: Path):
    readme = tmp_path / "README.md"
    readme.write_text(
        "My Setext Project\n===\n\nThis is a description line following Setext header.\nAnother line.",
        encoding="utf-8",
    )

    identity = get_project_identity(tmp_path)
    assert identity["project_name"] == "My Setext Project"
    assert identity["project_description"] == "This is a description line following Setext header."
