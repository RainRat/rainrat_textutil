import pytest
from unittest.mock import patch
import sourcecombine
import utils
import logging

def test_export_config_error_handling(tmp_path, monkeypatch, caplog):
    """Test that sourcecombine.main() handles errors during config export."""
    monkeypatch.chdir(tmp_path)

    # Use actual parser to get a valid Namespace with all defaults
    with patch("sys.argv", ["sourcecombine.py", "--export-config", "exported.yml"]):
        with patch("sourcecombine.utils.save_yaml_config", side_effect=utils.InvalidConfigError("Mocked error")):
            with caplog.at_level(logging.ERROR):
                with pytest.raises(SystemExit) as excinfo:
                    sourcecombine.main()

    assert excinfo.value.code == 1
    assert "Could not export configuration: Mocked error" in caplog.text
