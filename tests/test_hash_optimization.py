import hashlib
from pathlib import Path
from unittest.mock import patch, MagicMock
from sourcecombine import _render_template

def test_hash_calculation_optimization():
    # Setup
    template_with_hash = "Hash: {{HASH}}"
    template_without_hash = "Filename: {{FILENAME}}"
    relative_path = Path("test.py")
    content = "print('hello world')"

    # Test case 1: Template contains {{HASH}}
    with patch("hashlib.sha256") as mock_sha256:
        # We need to return a mock that has a hexdigest method
        mock_hash_obj = MagicMock()
        mock_sha256.return_value = mock_hash_obj
        mock_hash_obj.hexdigest.return_value = "mocked_hash"

        result = _render_template(template_with_hash, relative_path, content=content)

        assert "mocked_hash" in result
        mock_sha256.assert_called_once()

    # Test case 2: Template does NOT contain {{HASH}}
    with patch("hashlib.sha256") as mock_sha256:
        result = _render_template(template_without_hash, relative_path, content=content)

        assert "test.py" in result
        mock_sha256.assert_not_called()

if __name__ == "__main__":
    try:
        test_hash_calculation_optimization()
        print("Optimization test passed!")
    except AssertionError as e:
        print(f"Optimization test failed: {e}")
        exit(1)
    except Exception as e:
        print(f"An error occurred during testing: {e}")
        exit(1)
