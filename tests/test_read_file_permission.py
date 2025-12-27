from unittest.mock import patch
from pathlib import Path
from utils import read_file_best_effort

def test_read_file_handles_permission_error_on_open(tmp_path):
    """Verify that PermissionError (and other OSErrors) during file read are handled gracefully."""
    f = tmp_path / "protected.txt"
    f.touch()

    # Patch Path.read_bytes to raise PermissionError
    with patch("pathlib.Path.read_bytes", side_effect=PermissionError("Access denied")), \
         patch("logging.warning") as mock_log:
        content = read_file_best_effort(f)
        assert content == ""
        assert mock_log.called
        assert "Could not read" in str(mock_log.call_args)
