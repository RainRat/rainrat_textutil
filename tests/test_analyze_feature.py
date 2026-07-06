import sys; import os; from pathlib import Path; sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))

import sys
from unittest.mock import patch
import pytest
from sourcecombine import main

@pytest.fixture
def mock_argv():
    """Context manager to mock sys.argv."""
    def _mock_argv(args):
        return patch.object(sys, 'argv', ['sourcecombine.py'] + args)
    return _mock_argv

def test_analyze_preset_enables_flags(mock_argv):
    """Verify that --analyze enables dry_run, estimate_tokens, overview, and tree."""
    with mock_argv(['.', '--analyze']):
        # Patch find_and_combine_files to capture the config/arguments
        with patch('sourcecombine.find_and_combine_files') as mock_combine:
            mock_combine.return_value = {}
            try:
                main()
            except SystemExit:
                pass

            # Check if it was called (main might exit, but should call combine first)
            assert mock_combine.called
            args, kwargs = mock_combine.call_args

            # The config (first arg) should have these set if main logic applies them
            # Wait, main() sets them on the 'args' object, which then affects how
            # find_and_combine_files is called.

            # In sourcecombine.py:
            # stats = find_and_combine_files(
            #     config,
            #     output_path,
            #     dry_run=args.dry_run,
            #     ...
            #     estimate_tokens=args.estimate_tokens,
            #     ...
            #     tree_view=args.tree,
            #     ...
            # )

            assert kwargs['dry_run'] is True
            assert kwargs['estimate_tokens'] is True
            assert kwargs['tree_view'] is True

            # overview is used to update config['output']['project_overview']
            assert args[0]['output']['project_overview'] is True
